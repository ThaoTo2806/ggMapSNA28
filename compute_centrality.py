"""Compute node centralities for the cleaned, undirected restaurant graph."""

from __future__ import annotations

import argparse
import csv
import json
import random
from pathlib import Path
from typing import Any

import networkx as nx


def read_graph(processed_dir: Path) -> tuple[nx.Graph, dict[str, dict[str, str]], dict[str, int]]:
    nodes_path = processed_dir / "nodes.csv"
    edges_path = processed_dir / "edges.csv"
    if not nodes_path.is_file() or not edges_path.is_file():
        raise FileNotFoundError(
            f"Khong tim thay nodes.csv/edges.csv trong {processed_dir}. "
            "Hay chay py preprocess_data.py truoc."
        )

    graph = nx.Graph()
    node_rows: dict[str, dict[str, str]] = {}
    with nodes_path.open("r", encoding="utf-8-sig", newline="") as source:
        for row in csv.DictReader(source):
            node_id = (row.get("node_id") or row.get("Id") or "").strip()
            if not node_id:
                continue
            node_rows[node_id] = row
            graph.add_node(node_id)

    edge_stats = {"input_edges": 0, "skipped_edges": 0, "self_loops_skipped": 0}
    with edges_path.open("r", encoding="utf-8-sig", newline="") as source:
        for row in csv.DictReader(source):
            edge_stats["input_edges"] += 1
            left = (row.get("Source") or row.get("source") or "").strip()
            right = (row.get("Target") or row.get("target") or "").strip()
            if left not in node_rows or right not in node_rows:
                edge_stats["skipped_edges"] += 1
                continue
            if left == right:
                edge_stats["self_loops_skipped"] += 1
                continue
            graph.add_edge(left, right)

    return graph, node_rows, edge_stats


def sampled_path_centralities(
    graph: nx.Graph, sample_size: int, seed: int
) -> tuple[dict[str, float], dict[str, float], dict[str, float], int]:
    node_ids = list(graph.nodes)
    if not node_ids:
        return {}, {}, {}, 0

    actual_sample_size = min(sample_size, len(node_ids))
    sampled_sources = random.Random(seed).sample(node_ids, actual_sample_size)
    n = len(node_ids)
    distance_totals = dict.fromkeys(node_ids, 0.0)
    reachable_counts = dict.fromkeys(node_ids, 0.0)
    reciprocal_distance_totals = dict.fromkeys(node_ids, 0.0)

    for source_id in sampled_sources:
        distances = nx.single_source_shortest_path_length(graph, source_id)
        for target_id, distance in distances.items():
            if target_id == source_id:
                continue
            distance_totals[target_id] += distance
            reachable_counts[target_id] += 1
            reciprocal_distance_totals[target_id] += 1 / distance

    expansion = n / actual_sample_size
    closeness: dict[str, float] = {}
    harmonic: dict[str, float] = {}
    for node_id in node_ids:
        estimated_reachable = reachable_counts[node_id] * expansion
        estimated_distance_sum = distance_totals[node_id] * expansion
        reachable_other = max(0.0, estimated_reachable)
        if reachable_other > 0 and estimated_distance_sum > 0 and n > 1:
            closeness[node_id] = (
                (reachable_other / (n - 1))
                * (reachable_other / estimated_distance_sum)
            )
        else:
            closeness[node_id] = 0.0
        harmonic[node_id] = (
            reciprocal_distance_totals[node_id] * expansion / (n - 1)
            if n > 1
            else 0.0
        )

    return closeness, harmonic, distance_totals, actual_sample_size


def safe_metric(
    name: str, calculate: Any, node_ids: list[str], errors: dict[str, str]
) -> dict[str, float | None]:
    try:
        result = calculate()
        return {node_id: float(result[node_id]) for node_id in node_ids}
    except Exception as error:
        errors[name] = f"{type(error).__name__}: {error}"
        return {node_id: None for node_id in node_ids}


def write_node_metrics(
    path: Path,
    graph: nx.Graph,
    node_rows: dict[str, dict[str, str]],
    metrics: dict[str, dict[str, float | None]],
) -> None:
    fields = [
        "node_id",
        "name",
        "food_categories",
        "rating",
        "reviews_count",
        "degree",
        "degree_centrality",
        "betweenness_approx",
        "closeness_approx",
        "harmonic_centrality_approx",
        "eigenvector_centrality",
        "katz_centrality",
        "pagerank",
        "hits_hub",
        "hits_authority",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        for node_id in sorted(graph.nodes):
            source = node_rows[node_id]
            row: dict[str, object] = {
                "node_id": node_id,
                "name": source.get("name", ""),
                "food_categories": source.get("food_categories", ""),
                "rating": source.get("rating", ""),
                "reviews_count": source.get("reviews_count", ""),
                "degree": graph.degree(node_id),
            }
            for metric_name, values in metrics.items():
                row[metric_name] = values.get(node_id)
            writer.writerow(row)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Tinh centrality tren do thi nha hang da lam sach."
    )
    parser.add_argument("--input-dir", type=Path, default=Path("data/processed"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/processed"))
    parser.add_argument("--samples", type=int, default=500)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    if args.samples < 1:
        parser.error("--samples phai lon hon 0")

    graph, node_rows, edge_stats = read_graph(args.input_dir)
    node_ids = list(graph.nodes)
    n = len(node_ids)
    if n == 0:
        parser.error("Khong co node hop le trong nodes.csv")

    errors: dict[str, str] = {}
    degree_centrality = nx.degree_centrality(graph)
    sample_size = min(args.samples, n)
    betweenness = safe_metric(
        "betweenness_approx",
        lambda: nx.betweenness_centrality(
            graph,
            k=sample_size,
            normalized=True,
            weight=None,
            seed=args.seed,
        ),
        node_ids,
        errors,
    )
    closeness, harmonic, _, path_sample_size = sampled_path_centralities(
        graph, args.samples, args.seed
    )

    eigenvector = safe_metric(
        "eigenvector_centrality",
        lambda: nx.eigenvector_centrality(
            graph, max_iter=2000, tol=1e-7, weight=None
        ),
        node_ids,
        errors,
    )
    max_degree = max(dict(graph.degree()).values(), default=0)
    katz_alpha = 0.9 / (max_degree + 1)
    katz = safe_metric(
        "katz_centrality",
        lambda: nx.katz_centrality(
            graph,
            alpha=katz_alpha,
            beta=1.0,
            max_iter=2000,
            tol=1e-7,
            normalized=True,
            weight=None,
        ),
        node_ids,
        errors,
    )
    pagerank = safe_metric(
        "pagerank",
        lambda: nx.pagerank(graph, alpha=0.85, max_iter=1000, weight=None),
        node_ids,
        errors,
    )
    hits_hub, hits_authority = {}, {}
    try:
        hits_hub, hits_authority = nx.hits(
            graph, max_iter=3000, tol=1e-7, normalized=True
        )
        hits_hub = {node_id: float(hits_hub[node_id]) for node_id in node_ids}
        hits_authority = {
            node_id: float(hits_authority[node_id]) for node_id in node_ids
        }
    except Exception as error:
        errors["hits"] = f"{type(error).__name__}: {error}"
        hits_hub = {node_id: None for node_id in node_ids}
        hits_authority = {node_id: None for node_id in node_ids}

    metrics: dict[str, dict[str, float | None]] = {
        "degree_centrality": {
            node_id: float(degree_centrality[node_id]) for node_id in node_ids
        },
        "betweenness_approx": betweenness,
        "closeness_approx": closeness,
        "harmonic_centrality_approx": harmonic,
        "eigenvector_centrality": eigenvector,
        "katz_centrality": katz,
        "pagerank": pagerank,
        "hits_hub": hits_hub,
        "hits_authority": hits_authority,
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = args.output_dir / "centrality_scores.csv"
    write_node_metrics(metrics_path, graph, node_rows, metrics)

    components = list(nx.connected_components(graph))
    largest_component_size = max((len(component) for component in components), default=0)
    edge_count = graph.number_of_edges()
    summary = {
        "nodes": n,
        "edges": edge_count,
        "input_edge_rows": edge_stats["input_edges"],
        "skipped_edges": edge_stats["skipped_edges"],
        "self_loops_skipped": edge_stats["self_loops_skipped"],
        "components": len(components),
        "largest_component_nodes": largest_component_size,
        "density": nx.density(graph),
        "average_degree": (2 * edge_count / n) if n else 0,
        "metrics_file": metrics_path.name,
        "graph_interpretation": "undirected, unweighted; each edge is a restaurant pair within 1 km",
        "path_metric_method": "sampled-source estimates; not exact all-node values",
        "path_samples_requested": args.samples,
        "path_samples_used": path_sample_size,
        "random_seed": args.seed,
        "betweenness_method": "NetworkX sampled-source approximation",
        "closeness_method": "sampled-source estimates with disconnected-component correction",
        "harmonic_method": "sampled-source estimate normalized by node_count - 1",
        "katz_alpha": katz_alpha,
        "katz_alpha_bound": "0.9 / (maximum_degree + 1), below 1 / spectral_radius",
        "pagerank_damping": 0.85,
        "hits_note": "HITS on an undirected graph is mathematically degenerate; interpret hub/authority cautiously",
        "errors": errors,
    }
    summary_path = args.output_dir / "centrality_summary.json"
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()