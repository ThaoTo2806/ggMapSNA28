"""Clean Google Maps restaurant CSV files and build a spatial SNA graph."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import unicodedata
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from xml.sax.saxutils import quoteattr

from scipy.sparse import coo_matrix, save_npz
from scipy.spatial import cKDTree


EARTH_RADIUS_KM = 6371.0088
INPUT_PREFIX = re.compile(r"^dataset_google-maps[-_]", re.IGNORECASE)


def clean_text(value: object) -> str:
    if value is None:
        return ""
    return unicodedata.normalize("NFC", str(value)).strip()


def parse_number(value: object) -> float | None:
    text = clean_text(value).replace(",", ".")
    if not text:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def parse_count(value: object) -> int | None:
    number = parse_number(value)
    if number is None or number < 0:
        return None
    return int(number)


def category_from_filename(path: Path) -> str:
    return INPUT_PREFIX.sub("", path.stem).replace("-", " ").strip()


def stable_place_id(row: dict[str, str]) -> str:
    place_id = clean_text(row.get("placeId"))
    if place_id:
        return place_id

    url = clean_text(row.get("url"))
    if url:
        query_id = parse_qs(urlparse(url).query).get("query_place_id", [""])[0]
        if query_id:
            return query_id

    identity = "|".join(
        clean_text(row.get(field)).casefold() for field in ("title", "address")
    )
    return "fallback_" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20]


def read_records(input_dir: Path) -> tuple[dict[str, dict[str, object]], dict[str, int]]:
    records: dict[str, dict[str, object]] = {}
    stats = {"input_files": 0, "raw_records": 0, "invalid_records": 0}

    for csv_path in sorted(input_dir.glob("*.csv")):
        stats["input_files"] += 1
        file_category = category_from_filename(csv_path)
        with csv_path.open("r", encoding="utf-8-sig", newline="") as source:
            reader = csv.DictReader(source)
            required_columns = {"title", "location/lat", "location/lng"}
            missing = required_columns.difference(reader.fieldnames or [])
            if missing:
                raise ValueError(
                    f"{csv_path.name} thiếu cột bắt buộc: {', '.join(sorted(missing))}"
                )

            for row in reader:
                stats["raw_records"] += 1
                title = clean_text(row.get("title"))
                latitude = parse_number(row.get("location/lat"))
                longitude = parse_number(row.get("location/lng"))
                if (
                    not title
                    or latitude is None
                    or longitude is None
                    or not -90 <= latitude <= 90
                    or not -180 <= longitude <= 180
                ):
                    stats["invalid_records"] += 1
                    continue

                place_id = stable_place_id(row)
                record = records.get(place_id)
                if record is None:
                    record = {
                        "node_id": "place_" + place_id,
                        "place_id": place_id,
                        "name": title,
                        "address": clean_text(row.get("address")),
                        "city": clean_text(row.get("city")),
                        "maps_category": clean_text(row.get("categoryName")),
                        "latitude": latitude,
                        "longitude": longitude,
                        "rating": parse_number(row.get("totalScore")),
                        "reviews_count": parse_count(row.get("reviewsCount")),
                        "food_categories": set(),
                        "source_files": set(),
                    }
                    records[place_id] = record
                else:
                    for field in ("address", "city", "maps_category"):
                        if not record[field]:
                            value = (
                                row.get("categoryName")
                                if field == "maps_category"
                                else row.get(field)
                            )
                            record[field] = clean_text(value)
                    if record["rating"] is None:
                        record["rating"] = parse_number(row.get("totalScore"))
                    if record["reviews_count"] is None:
                        record["reviews_count"] = parse_count(row.get("reviewsCount"))

                record["food_categories"].add(file_category)
                record["source_files"].add(csv_path.name)

    return records, stats


def build_graph(
    records: dict[str, dict[str, object]], radius_km: float
) -> tuple[list[dict[str, object]], list[dict[str, object]], object]:
    nodes = sorted(records.values(), key=lambda record: str(record["node_id"]))
    for record in nodes:
        record["food_categories"] = "|".join(sorted(record["food_categories"]))
        record["source_files"] = "|".join(sorted(record["source_files"]))

    if len(nodes) < 2:
        return nodes, [], coo_matrix((len(nodes), len(nodes)), dtype="uint8").tocsr()

    latitudes = [math.radians(float(node["latitude"])) for node in nodes]
    longitudes = [math.radians(float(node["longitude"])) for node in nodes]
    unit_sphere_points = [
        (
            math.cos(latitude) * math.cos(longitude),
            math.cos(latitude) * math.sin(longitude),
            math.sin(latitude),
        )
        for latitude, longitude in zip(latitudes, longitudes)
    ]
    angular_radius = min(radius_km / EARTH_RADIUS_KM, math.pi)
    chord_radius = 2 * math.sin(angular_radius / 2)
    candidate_pairs = cKDTree(unit_sphere_points).query_pairs(chord_radius)

    edges: list[dict[str, object]] = []
    matrix_rows: list[int] = []
    matrix_columns: list[int] = []
    matrix_values: list[int] = []
    for left, right in sorted(candidate_pairs):
        delta_latitude = latitudes[left] - latitudes[right]
        delta_longitude = longitudes[left] - longitudes[right]
        haversine = (
            math.sin(delta_latitude / 2) ** 2
            + math.cos(latitudes[left])
            * math.cos(latitudes[right])
            * math.sin(delta_longitude / 2) ** 2
        )
        distance_km = 2 * EARTH_RADIUS_KM * math.asin(min(1.0, math.sqrt(haversine)))
        if distance_km > radius_km:
            continue

        edges.append(
            {
                "Source": nodes[left]["node_id"],
                "Target": nodes[right]["node_id"],
                "Type": "Undirected",
                "Weight": round(1 / max(distance_km, 1e-9), 6),
                "distance_km": round(distance_km, 6),
                "similarity_weight": round(1 / max(distance_km, 1e-9), 6),
            }
        )
        matrix_rows.extend((left, right))
        matrix_columns.extend((right, left))
        matrix_values.extend((1, 1))

    adjacency = coo_matrix(
        (matrix_values, (matrix_rows, matrix_columns)),
        shape=(len(nodes), len(nodes)),
        dtype="uint8",
    ).tocsr()
    return nodes, edges, adjacency


def write_csv(path: Path, rows: list[dict[str, object]], columns: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_gexf(
    path: Path, nodes: list[dict[str, object]], edges: list[dict[str, object]]
) -> None:
    node_attributes = [
        ("place_id", "string"),
        ("address", "string"),
        ("city", "string"),
        ("maps_category", "string"),
        ("food_categories", "string"),
        ("latitude", "double"),
        ("longitude", "double"),
        ("rating", "double"),
        ("reviews_count", "integer"),
        ("source_files", "string"),
    ]
    edge_attributes = [
        ("distance_km", "double"),
        ("similarity_weight", "double"),
    ]

    with path.open("w", encoding="utf-8", newline="") as output:
        output.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        output.write(
            '<gexf xmlns="http://www.gexf.net/1.2draft" version="1.2">\n'
            '  <meta lastmodifieddate="2026-10-24">\n'
            '    <creator>preprocess_data.py</creator>\n'
            '    <description>Restaurant locations connected within the configured radius</description>\n'
            '  </meta>\n'
            '  <graph mode="static" defaultedgetype="undirected">\n'
            '    <attributes class="node" mode="static">\n'
        )
        for attribute_id, attribute_type in node_attributes:
            output.write(
                f"      <attribute id={quoteattr(attribute_id)} "
                f"title={quoteattr(attribute_id)} type={quoteattr(attribute_type)} />\n"
            )
        output.write('    </attributes>\n    <attributes class="edge" mode="static">\n')
        for attribute_id, attribute_type in edge_attributes:
            output.write(
                f"      <attribute id={quoteattr(attribute_id)} "
                f"title={quoteattr(attribute_id)} type={quoteattr(attribute_type)} />\n"
            )
        output.write('    </attributes>\n    <nodes>\n')

        for node in nodes:
            output.write(
                f"      <node id={quoteattr(str(node['node_id']))} "
                f"label={quoteattr(str(node['name']))}>\n"
                '        <attvalues>\n'
            )
            for attribute_id, _ in node_attributes:
                value = node.get(attribute_id)
                if value is not None and value != "":
                    output.write(
                        f"          <attvalue for={quoteattr(attribute_id)} "
                        f"value={quoteattr(str(value))} />\n"
                    )
            output.write('        </attvalues>\n      </node>\n')

        output.write('    </nodes>\n    <edges>\n')
        for edge_id, edge in enumerate(edges):
            output.write(
                f"      <edge id={quoteattr(str(edge_id))} "
                f"source={quoteattr(str(edge['Source']))} "
                f"target={quoteattr(str(edge['Target']))} "
                'weight="1">\n'
                '        <attvalues>\n'
                f"          <attvalue for=\"distance_km\" "
                f"value={quoteattr(str(edge['distance_km']))} />\n"
                f"          <attvalue for=\"similarity_weight\" "
                f"value={quoteattr(str(edge['similarity_weight']))} />\n"
                '        </attvalues>\n'
                '      </edge>\n'
            )
        output.write('    </edges>\n  </graph>\n</gexf>\n')


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Lam sach CSV Google Maps va tao do thi dia diem gan nhau."
    )
    parser.add_argument("--input-dir", type=Path, default=Path("data/ggmap123"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/processed"))
    parser.add_argument("--radius-km", type=float, default=1.0)
    args = parser.parse_args()

    if args.radius_km <= 0:
        parser.error("--radius-km phai lon hon 0")
    if not args.input_dir.is_dir():
        parser.error(f"Khong tim thay thu muc input: {args.input_dir}")

    records, stats = read_records(args.input_dir)
    nodes, edges, adjacency = build_graph(records, args.radius_km)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    node_columns = [
        "Id",
        "Label",
        "node_id",
        "place_id",
        "name",
        "address",
        "city",
        "maps_category",
        "food_categories",
        "latitude",
        "longitude",
        "rating",
        "reviews_count",
        "source_files",
    ]
    gephi_nodes = [
        {**node, "Id": node["node_id"], "Label": node["name"]} for node in nodes
    ]
    write_csv(args.output_dir / "nodes.csv", gephi_nodes, node_columns)
    write_csv(
        args.output_dir / "edges.csv",
        edges,
        ["Source", "Target", "Type", "Weight", "distance_km", "similarity_weight"],
    )
    write_csv(
        args.output_dir / "node_index.csv",
        [
            {"matrix_index": index, "node_id": node["node_id"]}
            for index, node in enumerate(nodes)
        ],
        ["matrix_index", "node_id"],
    )
    save_npz(args.output_dir / "adjacency_matrix.npz", adjacency)
    gexf_path = args.output_dir / "restaurants_network.gexf"
    write_gexf(gexf_path, nodes, edges)

    summary = {
        **stats,
        "unique_nodes": len(nodes),
        "duplicate_records_removed": stats["raw_records"]
        - stats["invalid_records"]
        - len(nodes),
        "edges": len(edges),
        "gephi_file": gexf_path.name,
        "graph_type": "undirected simple spatial threshold graph",
        "edge_rule": "connect two distinct locations if Haversine distance <= radius_km",
        "radius_km": args.radius_km,
        "adjacency_matrix": {
            "file": "adjacency_matrix.npz",
            "format": "SciPy CSR sparse matrix",
            "values": "binary (1 = edge, 0 = no edge), symmetric, diagonal = 0",
            "node_order_file": "node_index.csv",
        },
        "edge_weights": {
            "distance_km": "Haversine distance; use as path cost",
            "similarity_weight": "1 / distance_km; use as connection strength",
        },
    }
    (args.output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()