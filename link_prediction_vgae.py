"""VGAE link prediction benchmark against CN, Jaccard, and Adamic-Adar."""

from __future__ import annotations

import argparse
import copy
import csv
import json
import math
import random
import time
from pathlib import Path
from typing import Any

import numpy as np
import scipy.sparse as sp
import torch
from sklearn.metrics import average_precision_score, roc_auc_score
from torch import nn


def load_graph(input_dir: Path) -> tuple[list[str], list[tuple[int, int]], dict[str, dict[str, str]]]:
    nodes_path = input_dir / "nodes.csv"
    edges_path = input_dir / "edges.csv"
    if not nodes_path.is_file() or not edges_path.is_file():
        raise FileNotFoundError(
            f"Can nodes.csv va edges.csv trong {input_dir}. "
            "Hay dua thu muc processed len Kaggle Dataset."
        )

    node_rows: dict[str, dict[str, str]] = {}
    with nodes_path.open("r", encoding="utf-8-sig", newline="") as source:
        for row in csv.DictReader(source):
            node_id = (row.get("node_id") or row.get("Id") or "").strip()
            if node_id:
                node_rows[node_id] = row
    node_ids = sorted(node_rows)
    node_to_index = {node_id: index for index, node_id in enumerate(node_ids)}

    edge_set: set[tuple[int, int]] = set()
    with edges_path.open("r", encoding="utf-8-sig", newline="") as source:
        for row in csv.DictReader(source):
            source_id = (row.get("Source") or row.get("source") or "").strip()
            target_id = (row.get("Target") or row.get("target") or "").strip()
            if source_id not in node_to_index or target_id not in node_to_index:
                continue
            left, right = node_to_index[source_id], node_to_index[target_id]
            if left != right:
                edge_set.add((min(left, right), max(left, right)))
    return node_ids, sorted(edge_set), node_rows


def split_edges(
    edges: list[tuple[int, int]], seed: int, validation_fraction: float, test_fraction: float
) -> tuple[list[tuple[int, int]], list[tuple[int, int]], list[tuple[int, int]]]:
    rng = np.random.default_rng(seed)
    order = rng.permutation(len(edges))
    test_count = max(1, int(len(edges) * test_fraction))
    validation_count = max(1, int(len(edges) * validation_fraction))
    if test_count + validation_count >= len(edges):
        raise ValueError("Qua it canh de chia train/validation/test.")
    test_indices = order[:test_count]
    validation_indices = order[test_count : test_count + validation_count]
    train_indices = order[test_count + validation_count :]
    return (
        [edges[int(index)] for index in train_indices],
        [edges[int(index)] for index in validation_indices],
        [edges[int(index)] for index in test_indices],
    )


def sample_negative_edges(
    count: int,
    node_count: int,
    positive_edges: set[tuple[int, int]],
    rng: np.random.Generator,
) -> list[tuple[int, int]]:
    negatives: set[tuple[int, int]] = set()
    max_possible = node_count * (node_count - 1) // 2
    if max_possible - len(positive_edges) < count:
        raise ValueError("Khong du cap node khong co canh de lay mau am.")
    while len(negatives) < count:
        batch_size = max(1024, (count - len(negatives)) * 2)
        left = rng.integers(0, node_count, size=batch_size)
        right = rng.integers(0, node_count, size=batch_size)
        for first, second in zip(left, right):
            if first == second:
                continue
            edge = (int(min(first, second)), int(max(first, second)))
            if edge not in positive_edges:
                negatives.add(edge)
                if len(negatives) == count:
                    break
    return sorted(negatives)


def normalized_adjacency(
    edge_list: list[tuple[int, int]], node_count: int, device: torch.device
) -> torch.Tensor:
    if edge_list:
        edge_array = np.asarray(edge_list, dtype=np.int64)
        rows = np.concatenate((edge_array[:, 0], edge_array[:, 1]))
        columns = np.concatenate((edge_array[:, 1], edge_array[:, 0]))
    else:
        rows = np.empty(0, dtype=np.int64)
        columns = np.empty(0, dtype=np.int64)

    diagonal = np.arange(node_count, dtype=np.int64)
    rows = np.concatenate((rows, diagonal))
    columns = np.concatenate((columns, diagonal))
    values = np.ones(len(rows), dtype=np.float32)
    adjacency = sp.coo_matrix((values, (rows, columns)), shape=(node_count, node_count)).tocsr()
    degree = np.asarray(adjacency.sum(axis=1)).ravel()
    inverse_sqrt_degree = np.power(np.maximum(degree, 1.0), -0.5)
    normalized = sp.diags(inverse_sqrt_degree) @ adjacency @ sp.diags(inverse_sqrt_degree)
    normalized = normalized.tocoo().astype(np.float32)
    indices = torch.from_numpy(np.vstack((normalized.row, normalized.col)).astype(np.int64))
    values_tensor = torch.from_numpy(normalized.data)
    return torch.sparse_coo_tensor(
        indices, values_tensor, size=normalized.shape, device=device
    ).coalesce()


class VariationalGraphAutoencoder(nn.Module):
    """Featureless two-layer GCN variational encoder with inner-product decoder."""

    def __init__(self, node_count: int, hidden_dim: int, latent_dim: int, dropout: float) -> None:
        super().__init__()
        self.node_embedding = nn.Parameter(torch.empty(node_count, hidden_dim))
        self.hidden_layer = nn.Linear(hidden_dim, hidden_dim)
        self.mean_layer = nn.Linear(hidden_dim, latent_dim)
        self.log_std_layer = nn.Linear(hidden_dim, latent_dim)
        self.dropout = nn.Dropout(dropout)
        nn.init.xavier_uniform_(self.node_embedding)

    def encode(self, adjacency: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        hidden = torch.sparse.mm(adjacency, self.node_embedding)
        hidden = torch.relu(self.hidden_layer(hidden))
        hidden = self.dropout(hidden)
        mean = torch.sparse.mm(adjacency, self.mean_layer(hidden))
        log_std = torch.sparse.mm(adjacency, self.log_std_layer(hidden)).clamp(-8, 4)
        return mean, log_std

    @staticmethod
    def decode(latent: torch.Tensor, edges: torch.Tensor) -> torch.Tensor:
        return (latent[edges[:, 0]] * latent[edges[:, 1]]).sum(dim=1)


def make_edge_tensor(edges: list[tuple[int, int]], device: torch.device) -> torch.Tensor:
    return torch.as_tensor(edges, dtype=torch.long, device=device).reshape(-1, 2)


def evaluate_embeddings(
    mean: torch.Tensor,
    positive_edges: list[tuple[int, int]],
    negative_edges: list[tuple[int, int]],
    device: torch.device,
) -> tuple[float, float, np.ndarray]:
    with torch.no_grad():
        positive_scores = torch.sigmoid(
            VariationalGraphAutoencoder.decode(mean, make_edge_tensor(positive_edges, device))
        ).cpu().numpy()
        negative_scores = torch.sigmoid(
            VariationalGraphAutoencoder.decode(mean, make_edge_tensor(negative_edges, device))
        ).cpu().numpy()
    labels = np.concatenate((np.ones(len(positive_scores)), np.zeros(len(negative_scores))))
    scores = np.concatenate((positive_scores, negative_scores))
    return float(roc_auc_score(labels, scores)), float(average_precision_score(labels, scores)), scores


def structural_scores(
    train_adjacency: sp.csr_matrix, candidate_edges: list[tuple[int, int]]
) -> dict[str, np.ndarray]:
    degrees = np.asarray(train_adjacency.sum(axis=1)).ravel()
    inverse_log_degree = np.zeros_like(degrees, dtype=np.float64)
    valid = degrees > 1
    inverse_log_degree[valid] = 1.0 / np.log(degrees[valid])

    common = np.empty(len(candidate_edges), dtype=np.float64)
    jaccard = np.empty(len(candidate_edges), dtype=np.float64)
    adamic_adar = np.empty(len(candidate_edges), dtype=np.float64)
    for index, (left, right) in enumerate(candidate_edges):
        left_neighbors = train_adjacency.indices[
            train_adjacency.indptr[left] : train_adjacency.indptr[left + 1]
        ]
        right_neighbors = train_adjacency.indices[
            train_adjacency.indptr[right] : train_adjacency.indptr[right + 1]
        ]
        shared = np.intersect1d(left_neighbors, right_neighbors, assume_unique=True)
        shared_count = len(shared)
        common[index] = shared_count
        union_count = degrees[left] + degrees[right] - shared_count
        jaccard[index] = shared_count / union_count if union_count else 0.0
        if shared_count:
            shared_degrees = degrees[shared]
            usable = shared_degrees > 1
            adamic_adar[index] = inverse_log_degree[shared[usable]].sum()
        else:
            adamic_adar[index] = 0.0
    return {"common_neighbors": common, "jaccard": jaccard, "adamic_adar": adamic_adar}


def calculate_metrics(labels: np.ndarray, scores: np.ndarray) -> dict[str, float]:
    return {
        "roc_auc": float(roc_auc_score(labels, scores)),
        "average_precision": float(average_precision_score(labels, scores)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="VGAE link prediction benchmark.")
    parser.add_argument("--input-dir", type=Path, default=Path("data/processed"))
    parser.add_argument("--output-dir", type=Path, default=Path("link_prediction_results"))
    parser.add_argument("--device", choices=("auto", "cuda", "cpu"), default="auto")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--patience", type=int, default=12)
    parser.add_argument("--train-edges-per-epoch", type=int, default=200000)
    parser.add_argument("--hidden-dim", type=int, default=64)
    parser.add_argument("--latent-dim", type=int, default=32)
    parser.add_argument("--validation-fraction", type=float, default=0.10)
    parser.add_argument("--test-fraction", type=float, default=0.10)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    if args.epochs < 1 or args.patience < 1 or args.train_edges_per_epoch < 1:
        parser.error("epochs, patience va train-edges-per-epoch phai lon hon 0")
    if not 0 < args.validation_fraction < 1 or not 0 < args.test_fraction < 1:
        parser.error("validation-fraction va test-fraction phai nam trong (0, 1)")
    if args.validation_fraction + args.test_fraction >= 1:
        parser.error("Tong validation-fraction va test-fraction phai nho hon 1")

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)
    device = torch.device(
        "cuda" if args.device == "auto" and torch.cuda.is_available() else
        "cpu" if args.device == "auto" else args.device
    )
    if device.type == "cuda" and not torch.cuda.is_available():
        parser.error("CUDA khong kha dung; bat GPU trong Kaggle hoac chon --device cpu")

    started_at = time.time()
    node_ids, all_edges, node_rows = load_graph(args.input_dir)
    node_count = len(node_ids)
    if node_count < 3 or not all_edges:
        parser.error("Do thi can it nhat 3 node va 1 edge")
    train_edges, validation_edges, test_edges = split_edges(
        all_edges, args.seed, args.validation_fraction, args.test_fraction
    )
    all_positive_edges = set(all_edges)
    train_rng = np.random.default_rng(args.seed + 1)
    validation_rng = np.random.default_rng(args.seed + 2)
    test_rng = np.random.default_rng(args.seed + 3)
    train_sample_count = min(args.train_edges_per_epoch, len(train_edges))
    train_negative_pool = sample_negative_edges(
        min(2 * train_sample_count, node_count * (node_count - 1) // 2 - len(all_positive_edges)),
        node_count,
        all_positive_edges,
        train_rng,
    )
    validation_negative = sample_negative_edges(
        len(validation_edges), node_count, all_positive_edges, validation_rng
    )
    test_negative = sample_negative_edges(
        len(test_edges), node_count, all_positive_edges, test_rng
    )

    device_name = torch.cuda.get_device_name(device) if device.type == "cuda" else "CPU"
    print(f"Graph: {node_count:,} nodes, {len(all_edges):,} edges; device: {device_name}")
    print(
        f"Split: train {len(train_edges):,}, validation {len(validation_edges):,}, "
        f"test {len(test_edges):,} positive edges"
    )

    train_adjacency = sp.coo_matrix(
        (
            np.ones(2 * len(train_edges), dtype=np.float32),
            (
                np.asarray([edge[0] for edge in train_edges] + [edge[1] for edge in train_edges]),
                np.asarray([edge[1] for edge in train_edges] + [edge[0] for edge in train_edges]),
            ),
        ),
        shape=(node_count, node_count),
    ).tocsr()
    norm_adjacency = normalized_adjacency(train_edges, node_count, device)

    model = VariationalGraphAutoencoder(node_count, args.hidden_dim, args.latent_dim, 0.3).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01, weight_decay=0.0)
    train_positive_array = np.asarray(train_edges, dtype=np.int64)
    train_negative_array = np.asarray(train_negative_pool, dtype=np.int64)
    validation_negative_tensor = make_edge_tensor(validation_negative, device)
    best_validation_auc = -math.inf
    best_state: dict[str, torch.Tensor] | None = None
    best_epoch = 0
    epochs_without_improvement = 0
    validation_labels = np.concatenate(
        (np.ones(len(validation_edges)), np.zeros(len(validation_negative)))
    )

    for epoch in range(1, args.epochs + 1):
        model.train()
        sampled_indices = train_rng.choice(
            len(train_positive_array), size=train_sample_count, replace=False
        )
        positive_batch = torch.as_tensor(train_positive_array[sampled_indices], device=device)
        negative_indices = train_rng.choice(
            len(train_negative_array), size=train_sample_count, replace=False
        )
        negative_batch = torch.as_tensor(train_negative_array[negative_indices], device=device)
        mean, log_std = model.encode(norm_adjacency)
        latent = mean + torch.randn_like(mean) * torch.exp(log_std)
        positive_logits = model.decode(latent, positive_batch)
        negative_logits = model.decode(latent, negative_batch)
        reconstruction_loss = nn.functional.binary_cross_entropy_with_logits(
            torch.cat((positive_logits, negative_logits)),
            torch.cat((torch.ones_like(positive_logits), torch.zeros_like(negative_logits))),
        )
        kl_loss = -0.5 * torch.mean(
            torch.sum(1 + 2 * log_std - mean.square() - torch.exp(2 * log_std), dim=1)
        )
        loss = reconstruction_loss + kl_loss
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        optimizer.step()

        model.eval()
        with torch.no_grad():
            validation_mean, _ = model.encode(norm_adjacency)
            positive_validation_scores = torch.sigmoid(
                model.decode(validation_mean, make_edge_tensor(validation_edges, device))
            ).cpu().numpy()
            negative_validation_scores = torch.sigmoid(
                model.decode(validation_mean, validation_negative_tensor)
            ).cpu().numpy()
        validation_scores = np.concatenate(
            (positive_validation_scores, negative_validation_scores)
        )
        validation_auc = float(roc_auc_score(validation_labels, validation_scores))
        if validation_auc > best_validation_auc + 1e-5:
            best_validation_auc = validation_auc
            best_epoch = epoch
            best_state = {
                name: value.detach().cpu().clone()
                for name, value in model.state_dict().items()
            }
            epochs_without_improvement = 0
        else:
            epochs_without_improvement += 1
        if epoch == 1 or epoch % 10 == 0:
            print(
                f"Epoch {epoch:03d} | loss {loss.item():.4f} | "
                f"val ROC-AUC {validation_auc:.4f} | best {best_validation_auc:.4f}"
            )
        if epochs_without_improvement >= args.patience:
            print(f"Early stopping at epoch {epoch}; best epoch {best_epoch}.")
            break

    if best_state is None:
        raise RuntimeError("VGAE training did not produce a validation checkpoint.")
    model.load_state_dict(best_state)
    model.to(device).eval()
    with torch.no_grad():
        test_mean, _ = model.encode(norm_adjacency)
        vgae_auc, vgae_ap, vgae_scores = evaluate_embeddings(
            test_mean, test_edges, test_negative, device
        )

    test_candidates = test_edges + test_negative
    test_labels = np.concatenate((np.ones(len(test_edges)), np.zeros(len(test_negative))))
    print("Scoring structural baselines on the held-out test candidates...")
    baseline_scores = structural_scores(train_adjacency, test_candidates)
    results: dict[str, dict[str, float]] = {}
    for method, scores in baseline_scores.items():
        results[method] = calculate_metrics(test_labels, scores)
    results["VGAE"] = {"roc_auc": vgae_auc, "average_precision": vgae_ap}

    args.output_dir.mkdir(parents=True, exist_ok=True)
    predictions_path = args.output_dir / "test_predictions.csv"
    with predictions_path.open("w", encoding="utf-8-sig", newline="") as output:
        fields = ["source", "target", "label", "common_neighbors", "jaccard", "adamic_adar", "vgae_score"]
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        for index, (left, right) in enumerate(test_candidates):
            writer.writerow(
                {
                    "source": node_ids[left],
                    "target": node_ids[right],
                    "label": int(index < len(test_edges)),
                    "common_neighbors": baseline_scores["common_neighbors"][index],
                    "jaccard": baseline_scores["jaccard"][index],
                    "adamic_adar": baseline_scores["adamic_adar"][index],
                    "vgae_score": vgae_scores[index],
                }
            )

    summary = {
        "algorithm": "Variational Graph Autoencoder (VGAE), featureless two-layer GCN encoder, inner-product decoder",
        "question": "Does structural node embedding improve held-out edge prediction over CN, Jaccard, and Adamic-Adar?",
        "device": str(device),
        "device_name": device_name,
        "nodes": node_count,
        "observed_edges": len(all_edges),
        "train_positive_edges": len(train_edges),
        "validation_positive_edges": len(validation_edges),
        "test_positive_edges": len(test_edges),
        "test_negative_edges": len(test_negative),
        "split_fractions": {
            "train": 1 - args.validation_fraction - args.test_fraction,
            "validation": args.validation_fraction,
            "test": args.test_fraction,
        },
        "seed": args.seed,
        "best_epoch": best_epoch,
        "validation_roc_auc": best_validation_auc,
        "epochs_requested": args.epochs,
        "hidden_dim": args.hidden_dim,
        "latent_dim": args.latent_dim,
        "train_edges_per_epoch": train_sample_count,
        "candidate_negatives": "sampled uniformly from non-edges of the full observed graph; held-out positives excluded",
        "split_note": "random edge holdout; all validation/test positive edges are removed from the training graph",
        "interpretation_limit": "This is held-out prediction in a spatial proximity graph, not prediction of future social/business ties.",
        "test_metrics": results,
        "predictions_file": predictions_path.name,
        "elapsed_seconds": round(time.time() - started_at, 2),
    }
    summary_path = args.output_dir / "link_prediction_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Results saved in: {args.output_dir.resolve()}")


if __name__ == "__main__":
    main()
