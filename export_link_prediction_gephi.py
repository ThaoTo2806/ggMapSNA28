"""Export top held-out link predictions as a compact Gephi GEXF graph."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from xml.sax.saxutils import quoteattr


METHOD_COLUMNS = {
    "VGAE": "vgae_score",
    "Common Neighbors": "common_neighbors",
    "Jaccard": "jaccard",
    "Adamic-Adar": "adamic_adar",
}
NODE_ATTRIBUTES = [
    ("food_categories", "string"),
    ("city", "string"),
    ("maps_category", "string"),
    ("rating", "double"),
    ("reviews_count", "integer"),
    ("latitude", "double"),
    ("longitude", "double"),
    ("degree", "integer"),
    ("degree_centrality", "double"),
    ("betweenness_approx", "double"),
    ("closeness_approx", "double"),
    ("harmonic_centrality_approx", "double"),
    ("eigenvector_centrality", "double"),
    ("katz_centrality", "double"),
    ("pagerank", "double"),
]
EDGE_ATTRIBUTES = [
    ("test_label", "integer"),
    ("selected_by", "string"),
    ("vgae_score", "double"),
    ("common_neighbors", "double"),
    ("jaccard", "double"),
    ("adamic_adar", "double"),
]


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise FileNotFoundError(f"Khong tim thay file: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        return list(csv.DictReader(source))


def read_nodes(processed_dir: Path) -> dict[str, dict[str, str]]:
    node_rows = read_rows(processed_dir / "nodes.csv")
    nodes: dict[str, dict[str, str]] = {}
    for row in node_rows:
        node_id = (row.get("node_id") or row.get("Id") or "").strip()
        if node_id:
            nodes[node_id] = row

    centrality_path = processed_dir / "centrality_scores.csv"
    if centrality_path.is_file():
        for row in read_rows(centrality_path):
            node_id = (row.get("node_id") or "").strip()
            if node_id in nodes:
                nodes[node_id].update(row)
    return nodes


def select_edges(
    rows: list[dict[str, str]], top_k: int
) -> tuple[dict[tuple[str, str], dict[str, object]], dict[str, dict[str, int]]]:
    ranked_rows: dict[str, list[dict[str, str]]] = {}
    for method, column in METHOD_COLUMNS.items():
        ranked_rows[method] = sorted(
            (row for row in rows if row.get(column, "").strip()),
            key=lambda row: (-float(row[column]), row["source"], row["target"]),
        )

    selected: dict[tuple[str, str], dict[str, object]] = {}
    counts: dict[str, dict[str, int]] = {}
    for method, method_rows in ranked_rows.items():
        top_rows = method_rows[:top_k]
        bottom_rows = method_rows[-top_k:]
        counts[method] = {"top": len(top_rows), "bottom": len(bottom_rows)}
        for tail, selected_rows in (("top", top_rows), ("bottom", bottom_rows)):
            for row in selected_rows:
                source = row["source"].strip()
                target = row["target"].strip()
                if not source or not target or source == target:
                    continue
                key = tuple(sorted((source, target)))
                edge = selected.setdefault(
                    key,
                    {
                        "source": key[0],
                        "target": key[1],
                        "label": int(row["label"]),
                        "selected_by": set(),
                        "vgae_score": row.get("vgae_score", ""),
                        "common_neighbors": row.get("common_neighbors", ""),
                        "jaccard": row.get("jaccard", ""),
                        "adamic_adar": row.get("adamic_adar", ""),
                    },
                )
                if int(row["label"]) != edge["label"]:
                    raise ValueError(f"Cap test co mau label khong nhat quan: {key}")
                edge["selected_by"].add(f"{method}:{tail}")
    return selected, counts


def write_gexf(
    path: Path,
    nodes: dict[str, dict[str, str]],
    edges: dict[tuple[str, str], dict[str, object]],
) -> None:
    selected_node_ids = sorted(
        {node_id for edge in edges.values() for node_id in (edge["source"], edge["target"])}
    )
    missing_nodes = [node_id for node_id in selected_node_ids if node_id not in nodes]
    if missing_nodes:
        raise ValueError(
            f"{len(missing_nodes)} node trong du doan khong co trong nodes.csv; "
            f"vi du: {missing_nodes[0]}"
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as output:
        output.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        output.write(
            '<gexf xmlns="http://www.gexf.net/1.2draft" version="1.2">\n'
            '  <meta lastmodifieddate="2026-10-24">\n'
            '    <creator>export_link_prediction_gephi.py</creator>\n'
            '    <description>Top held-out link prediction candidates, selected by model rank</description>\n'
            '  </meta>\n'
            '  <graph mode="static" defaultedgetype="undirected">\n'
            '    <attributes class="node" mode="static">\n'
        )
        for index, (title, value_type) in enumerate(NODE_ATTRIBUTES):
            output.write(
                f"      <attribute id={quoteattr(str(index))} "
                f"title={quoteattr(title)} type={quoteattr(value_type)} />\n"
            )
        output.write('    </attributes>\n    <attributes class="edge" mode="static">\n')
        for index, (title, value_type) in enumerate(EDGE_ATTRIBUTES):
            output.write(
                f"      <attribute id={quoteattr(str(index))} "
                f"title={quoteattr(title)} type={quoteattr(value_type)} />\n"
            )
        output.write('    </attributes>\n    <nodes>\n')

        for node_id in selected_node_ids:
            row = nodes[node_id]
            label = row.get("name") or row.get("Label") or node_id
            output.write(
                f"      <node id={quoteattr(node_id)} label={quoteattr(label)}>\n"
                '        <attvalues>\n'
            )
            for index, (title, _) in enumerate(NODE_ATTRIBUTES):
                value = row.get(title, "").strip()
                if value:
                    output.write(
                        f"          <attvalue for={quoteattr(str(index))} "
                        f"value={quoteattr(value)} />\n"
                    )
            output.write('        </attvalues>\n      </node>\n')

        output.write('    </nodes>\n    <edges>\n')
        ordered_edges = sorted(edges.values(), key=lambda edge: (edge["source"], edge["target"]))
        for edge_id, edge in enumerate(ordered_edges):
            true_label = int(edge["label"])
            edge_label = "Held-out positive" if true_label == 1 else "Sampled negative"
            output.write(
                f"      <edge id={quoteattr(str(edge_id))} "
                f"source={quoteattr(str(edge['source']))} "
                f"target={quoteattr(str(edge['target']))} "
                f"label={quoteattr(edge_label)} weight=\"1\">\n"
                '        <attvalues>\n'
            )
            values = {
                "test_label": str(true_label),
                "selected_by": "|".join(sorted(edge["selected_by"])),
                "vgae_score": str(edge["vgae_score"]),
                "common_neighbors": str(edge["common_neighbors"]),
                "jaccard": str(edge["jaccard"]),
                "adamic_adar": str(edge["adamic_adar"]),
            }
            for index, (title, _) in enumerate(EDGE_ATTRIBUTES):
                value = values[title]
                if value:
                    output.write(
                        f"          <attvalue for={quoteattr(str(index))} "
                        f"value={quoteattr(value)} />\n"
                    )
            output.write('        </attvalues>\n      </edge>\n')
        output.write('    </edges>\n  </graph>\n</gexf>\n')


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export held-out link prediction results for direct Gephi viewing."
    )
    parser.add_argument("--processed-dir", type=Path, default=Path("data/processed"))
    parser.add_argument("--results-dir", type=Path, default=Path("link_prediction_results"))
    parser.add_argument("--top-k", type=int, default=500)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("link_prediction_results/link_prediction_gephi.gexf"),
    )
    args = parser.parse_args()
    if args.top_k < 1:
        parser.error("--top-k phai lon hon 0")

    nodes = read_nodes(args.processed_dir)
    predictions = read_rows(args.results_dir / "test_predictions.csv")
    selected_edges, selected_counts = select_edges(predictions, args.top_k)
    if not selected_edges:
        parser.error("Khong co canh nao duoc chon tu test_predictions.csv")

    write_gexf(args.output, nodes, selected_edges)
    output_summary = {
        "output_file": str(args.output),
        "test_candidate_rows": len(predictions),
        "top_k_per_method": args.top_k,
        "selected_per_method": selected_counts,
        "unique_selected_edges": len(selected_edges),
        "selected_nodes": len(
            {node_id for edge in selected_edges.values() for node_id in (edge["source"], edge["target"])}
        ),
        "positive_edges": sum(int(edge["label"]) for edge in selected_edges.values()),
        "negative_edges": sum(1 - int(edge["label"]) for edge in selected_edges.values()),
        "note": "Top- and bottom-ranked held-out test candidates only; this is not the full observed graph.",
    }
    print(json.dumps(output_summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
