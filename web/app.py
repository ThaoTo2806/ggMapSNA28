from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"
LINK_RESULTS_DIR = ROOT / "link_prediction_results"
CENTRALITY_COLUMNS = {
    "degree": "Bậc (Degree)",
    "degree_centrality": "Degree centrality",
    "betweenness_approx": "Betweenness (ước lượng)",
    "closeness_approx": "Closeness (ước lượng)",
    "harmonic_centrality_approx": "Harmonic (ước lượng)",
    "eigenvector_centrality": "Eigenvector",
    "katz_centrality": "Katz",
    "pagerank": "PageRank",
    "hits_hub": "HITS hub",
    "hits_authority": "HITS authority",
}
METHOD_LABELS = {
    "common_neighbors": "Common Neighbors",
    "jaccard": "Jaccard",
    "adamic_adar": "Adamic-Adar",
    "vgae_score": "VGAE",
}

st.set_page_config(
    page_title="Mạng lưới Ẩm thực TP.HCM",
    page_icon="🍜",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@500;600;700;800&display=swap');
    :root { --ink:#152a2a; --muted:#607371; --paper:#f4f7f3; --green:#24735f; --lime:#d6ec72; --coral:#df7059; }
    html, body, [class*="css"] { font-family:'DM Sans', sans-serif; color:var(--ink); }
    .stApp { background:linear-gradient(135deg,#f4f7f3 0%,#edf3ef 55%,#f8f2e8 100%); }
    h1,h2,h3 { font-family:'Manrope','DM Sans',sans-serif; letter-spacing:0; color:var(--ink); }
    .hero { padding:1.2rem 1.5rem; border-radius:10px; background:#173c36; color:#f7f8ed; margin-bottom:1rem; }
    .hero-kicker { color:#d6ec72; font-size:.78rem; text-transform:uppercase; font-weight:700; }
    .hero-title { color:#f7f8ed; font-family:'Manrope',sans-serif; font-size:2rem; font-weight:800; margin:.25rem 0; }
    .hero-copy { color:#d5e2d8; margin:0; }
    .metric-card { background:#fff; border:1px solid #dce6df; border-top:3px solid #24735f; border-radius:8px; padding:1rem 1.1rem; min-height:104px; }
    .metric-label { color:#607371; font-size:.78rem; font-weight:600; }
    .metric-value { color:#173c36; font-family:'Manrope',sans-serif; font-size:1.7rem; font-weight:800; margin-top:.35rem; }
    .section-note { color:#607371; font-size:.9rem; }
    div[data-testid="stMetric"] { background:#fff; border:1px solid #dce6df; border-radius:8px; padding:.8rem 1rem; }
    div[data-testid="stMetricLabel"] { color:#607371; }
    div[data-testid="stDataFrame"] { border:1px solid #dce6df; border-radius:8px; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner="Đang đọc dữ liệu đã xử lý...")
def load_json(path: str) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as source:
        return json.load(source)


@st.cache_data(show_spinner="Đang tải bảng địa điểm và centrality...")
def load_places(processed_dir: str) -> pd.DataFrame:
    directory = Path(processed_dir)
    places = pd.read_csv(directory / "nodes.csv", low_memory=False)
    scores = pd.read_csv(directory / "centrality_scores.csv", low_memory=False)
    if "node_id" not in places.columns or "node_id" not in scores.columns:
        raise ValueError("nodes.csv và centrality_scores.csv cần có cột node_id")
    attributes = [
        column
        for column in ["node_id", "address", "city", "maps_category", "latitude", "longitude"]
        if column in places.columns
    ]
    return scores.merge(places[attributes], on="node_id", how="left", validate="one_to_one")


@st.cache_data(show_spinner="Đang tải kết quả dự đoán...")
def load_predictions(results_dir: str) -> pd.DataFrame:
    return pd.read_csv(Path(results_dir) / "test_predictions.csv", low_memory=False)


def show_metric_card(label: str, value: str) -> None:
    st.markdown(
        f'<div class="metric-card"><div class="metric-label">{label}</div>'
        f'<div class="metric-value">{value}</div></div>',
        unsafe_allow_html=True,
    )


def format_number(value: float | int) -> str:
    return f"{value:,.0f}".replace(",", ".")


def render_overview(
    places: pd.DataFrame, data_summary: dict[str, Any], centrality_summary: dict[str, Any], link_summary: dict[str, Any]
) -> None:
    st.markdown(
        '<div class="hero"><div class="hero-kicker">Social Network Analysis · Giai đoạn 5</div>'
        '<div class="hero-title">Mạng lưới Ẩm thực TP.HCM</div>'
        '<p class="hero-copy">Khám phá cấu trúc địa điểm, centrality và kết quả dự đoán liên kết.</p></div>',
        unsafe_allow_html=True,
    )
    first, second, third, fourth = st.columns(4)
    with first:
        show_metric_card("ĐỊA ĐIỂM", format_number(data_summary.get("unique_nodes", len(places))))
    with second:
        show_metric_card("LIÊN KẾT LÂN CẬN", format_number(data_summary.get("edges", centrality_summary.get("edges", 0))))
    with third:
        show_metric_card("THÀNH PHẦN LIÊN THÔNG", format_number(centrality_summary.get("components", 0)))
    with fourth:
        vgae = link_summary.get("test_metrics", {}).get("VGAE", {}).get("roc_auc", float("nan"))
        show_metric_card("VGAE ROC-AUC", f"{vgae:.3f}" if pd.notna(vgae) else "Chưa có")

    left, right = st.columns([1.15, 1])
    with left:
        st.subheader("Phân bố số láng giềng")
        if "degree" in places.columns:
            chart = px.histogram(
                places,
                x="degree",
                nbins=50,
                log_y=True,
                color_discrete_sequence=["#24735f"],
                labels={"degree": "Số láng giềng", "count": "Số địa điểm"},
            )
            chart.update_layout(height=360, margin=dict(l=10, r=10, t=20, b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(chart, use_container_width=True)
    with right:
        st.subheader("So sánh dự đoán liên kết")
        test_metrics = link_summary.get("test_metrics", {})
        metric_rows = [
            {"Phương pháp": METHOD_LABELS.get(key, key), "ROC-AUC": values.get("roc_auc"), "Average Precision": values.get("average_precision")}
            for key, values in test_metrics.items()
        ]
        if metric_rows:
            comparison = pd.DataFrame(metric_rows).melt(
                id_vars="Phương pháp", var_name="Chỉ số", value_name="Điểm"
            )
            chart = px.bar(
                comparison,
                x="Phương pháp",
                y="Điểm",
                color="Chỉ số",
                barmode="group",
                color_discrete_sequence=["#24735f", "#df7059"],
            )
            chart.update_layout(height=360, margin=dict(l=10, r=10, t=20, b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", legend_title_text="")
            st.plotly_chart(chart, use_container_width=True)
    st.caption(
        "Mạng được tạo bằng cách nối hai địa điểm cách nhau tối đa 1 km. "
        "Các số liệu mô tả cấu trúc địa lý, không khẳng định quan hệ xã hội hay kinh doanh."
    )


def render_places(places: pd.DataFrame) -> None:
    st.title("Địa điểm & centrality")
    st.caption("Lọc và xếp hạng địa điểm theo các độ đo giai đoạn 2; vị trí bản đồ lấy từ tọa độ crawl.")
    controls = st.columns([1, 1, 1.4])
    metric_col = controls[0].selectbox(
        "Xếp hạng theo",
        options=[column for column in CENTRALITY_COLUMNS if column in places.columns],
        format_func=lambda column: CENTRALITY_COLUMNS[column],
    )
    categories = sorted(
        {
            category.strip()
            for value in places.get("food_categories", pd.Series(dtype=str)).dropna().astype(str)
            for category in value.split("|")
            if category.strip()
        }
    )
    selected_category = controls[1].selectbox("Nhóm món", ["Tất cả"] + categories)
    search = controls[2].text_input("Tìm tên địa điểm", placeholder="Nhập tên quán...")

    filtered = places.copy()
    if selected_category != "Tất cả":
        filtered = filtered[filtered["food_categories"].fillna("").str.split("|").apply(lambda values: selected_category in values)]
    if search.strip():
        filtered = filtered[filtered["name"].fillna("").str.contains(search.strip(), case=False, regex=False)]
    filtered[metric_col] = pd.to_numeric(filtered[metric_col], errors="coerce")
    filtered = filtered.sort_values(metric_col, ascending=False, na_position="last")

    top_count = st.slider("Số kết quả trong bảng", min_value=10, max_value=100, value=25, step=5)
    display_columns = list(dict.fromkeys([
        column for column in ["name", "food_categories", "city", "rating", "reviews_count", "degree", metric_col]
        if column in filtered.columns
    ]))
    st.dataframe(filtered[display_columns].head(top_count), use_container_width=True, hide_index=True)

    if {"latitude", "longitude"}.issubset(filtered.columns):
        map_rows = filtered.dropna(subset=["latitude", "longitude"]).copy()
        map_rows["latitude"] = pd.to_numeric(map_rows["latitude"], errors="coerce")
        map_rows["longitude"] = pd.to_numeric(map_rows["longitude"], errors="coerce")
        map_rows = map_rows.dropna(subset=["latitude", "longitude"]).head(5000)
        st.subheader("Bản đồ địa điểm")
        st.caption(f"Đang hiển thị tối đa 5.000 kết quả đầu theo thứ hạng ({len(map_rows):,} điểm).")
        if not map_rows.empty:
            st.map(map_rows, latitude="latitude", longitude="longitude", size=20, color="#24735f", zoom=10, height=520)


def render_link_prediction(results_dir: Path, summary: dict[str, Any]) -> None:
    st.title("Dự đoán liên kết")
    st.caption("So sánh VGAE với các baseline trên tập test giai đoạn 3.")
    results = summary.get("test_metrics", {})
    comparison_rows = [
        {
            "Phương pháp": METHOD_LABELS.get(method, method),
            "ROC-AUC": values.get("roc_auc"),
            "Average Precision": values.get("average_precision"),
        }
        for method, values in results.items()
    ]
    st.dataframe(pd.DataFrame(comparison_rows).sort_values("ROC-AUC", ascending=False), use_container_width=True, hide_index=True)
    st.info(
        f"Chạy trên {summary.get('device_name', 'thiết bị chưa ghi nhận')}; "
        f"VGAE chọn epoch {summary.get('best_epoch', 'N/A')}. "
        "Cặp âm là negative sample, không chứng minh không tồn tại quan hệ ngoài đời."
    )

    prediction_path = results_dir / "test_predictions.csv"
    if not prediction_path.is_file():
        st.warning("Không tìm thấy test_predictions.csv để tra cứu từng cặp.")
        return
    predictions = load_predictions(str(results_dir))
    controls = st.columns([1, 1, 1])
    method_col = controls[0].selectbox(
        "Xếp hạng theo", options=list(METHOD_LABELS), format_func=lambda key: METHOD_LABELS[key]
    )
    label_selection = controls[1].selectbox(
        "Loại cặp", options=["Tất cả", "Positive thật", "Negative sample"]
    )
    row_count = controls[2].selectbox("Số dòng", [20, 50, 100], index=0)
    subset = predictions.copy()
    if label_selection == "Positive thật":
        subset = subset[subset["label"] == 1]
    elif label_selection == "Negative sample":
        subset = subset[subset["label"] == 0]
    subset[method_col] = pd.to_numeric(subset[method_col], errors="coerce")
    subset = subset.sort_values(method_col, ascending=False).head(row_count)
    node_lookup = load_places(str(PROCESSED_DIR)).set_index("node_id")["name"].to_dict()
    subset["Tên địa điểm 1"] = subset["source"].map(node_lookup)
    subset["Tên địa điểm 2"] = subset["target"].map(node_lookup)
    subset["Nhãn test"] = subset["label"].map({1: "Positive thật", 0: "Negative sample"})
    subset["Điểm phương pháp"] = subset[method_col]
    display = subset[["Tên địa điểm 1", "Tên địa điểm 2", "Nhãn test", "Điểm phương pháp", "vgae_score", "common_neighbors", "jaccard", "adamic_adar"]]
    st.subheader("Các cặp ứng viên được xếp hạng cao")
    st.dataframe(display, use_container_width=True, hide_index=True)


def main() -> None:
    required = [
        PROCESSED_DIR / "nodes.csv",
        PROCESSED_DIR / "centrality_scores.csv",
        PROCESSED_DIR / "summary.json",
        PROCESSED_DIR / "centrality_summary.json",
        LINK_RESULTS_DIR / "link_prediction_summary.json",
    ]
    missing = [path for path in required if not path.is_file()]
    if missing:
        st.error("Thiếu đầu ra của các giai đoạn trước:")
        for path in missing:
            st.code(str(path.relative_to(ROOT)))
        st.info("Chạy lần lượt preprocess_data.py, compute_centrality.py và link_prediction_vgae.py trước khi mở dashboard.")
        st.stop()

    try:
        places = load_places(str(PROCESSED_DIR))
        data_summary = load_json(str(PROCESSED_DIR / "summary.json"))
        centrality_summary = load_json(str(PROCESSED_DIR / "centrality_summary.json"))
        link_summary = load_json(str(LINK_RESULTS_DIR / "link_prediction_summary.json"))
    except (OSError, ValueError, pd.errors.ParserError) as error:
        st.error(f"Không đọc được dữ liệu đầu vào: {error}")
        st.stop()

    with st.sidebar:
        st.markdown("### MẠNG LƯỚI ẨM THỰC")
        st.caption("TP.HCM · SNA · Link prediction")
        page = st.radio("Điều hướng", ["Tổng quan", "Địa điểm & centrality", "Dự đoán liên kết"], label_visibility="collapsed")
        st.divider()
        st.caption(f"{len(places):,} địa điểm đã nạp")
        st.caption(f"Bán kính cạnh: {data_summary.get('radius_km', 'N/A')} km")
        st.caption("Nguồn: các bảng đã xử lý trong thư mục data/processed")

    if page == "Tổng quan":
        render_overview(places, data_summary, centrality_summary, link_summary)
    elif page == "Địa điểm & centrality":
        render_places(places)
    else:
        render_link_prediction(LINK_RESULTS_DIR, link_summary)


if __name__ == "__main__":
    main()
