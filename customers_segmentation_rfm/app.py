from datetime import timedelta

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import streamlit as st

st.set_page_config(page_title="Customer Segmentation | RFM", layout="wide")
st.title("Customer Segmentation — RFM Analysis")
st.caption("Find your best customers and prioritize retention campaigns.")


@st.cache_data
def generate_sample() -> pd.DataFrame:
    rng = np.random.default_rng(42)
    customers = [f"CUST_{i:04d}" for i in range(1, 501)]
    today = pd.Timestamp("2025-12-31")
    rows = []
    for customer in customers:
        orders = int(rng.integers(1, 15))
        for _ in range(orders):
            order_date = today - pd.Timedelta(days=int(rng.integers(1, 400)))
            rows.append(
                {
                    "date": order_date,
                    "customer_id": customer,
                    "sales": float(rng.integers(20, 1000)),
                }
            )
    return pd.DataFrame(rows)


def prepare_data(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    frame.columns = frame.columns.str.strip().str.lower().str.replace(" ", "_")
    aliases = {"order_date": "date", "customer": "customer_id", "revenue": "sales"}
    frame = frame.rename(columns=aliases)
    required = {"date", "customer_id", "sales"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(sorted(missing)))

    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["sales"] = pd.to_numeric(frame["sales"], errors="coerce")
    frame["customer_id"] = frame["customer_id"].astype("string").str.strip()
    frame = frame.dropna(subset=["date", "customer_id", "sales"])
    frame = frame[(frame["customer_id"] != "") & (frame["sales"] >= 0)]
    if frame.empty:
        raise ValueError("No usable sales rows were found in the uploaded file.")
    return frame


def quintile(series: pd.Series, higher_is_better: bool = True) -> pd.Series:
    rank = series.rank(method="first", pct=True, ascending=True)
    score = np.ceil(rank * 5).clip(1, 5).astype(int)
    return score if higher_is_better else 6 - score


uploaded = st.sidebar.file_uploader(
    "Upload sales CSV", type=["csv"], help="Required columns: date, customer_id, sales"
)
if uploaded:
    try:
        data = prepare_data(pd.read_csv(uploaded))
    except (ValueError, pd.errors.ParserError, UnicodeDecodeError) as exc:
        st.error(str(exc))
        st.stop()
    st.sidebar.caption("Showing results from your uploaded data.")
else:
    data = generate_sample()
    st.info("Showing reproducible sample data for 500 simulated customers.")

snapshot_date = data["date"].max().normalize() + timedelta(days=1)
rfm = (
    data.groupby("customer_id", as_index=False)
    .agg(
        recency=("date", lambda dates: (snapshot_date - dates.max()).days),
        frequency=("date", "count"),
        monetary=("sales", "sum"),
    )
)
rfm["r_score"] = quintile(rfm["recency"], higher_is_better=False)
rfm["f_score"] = quintile(rfm["frequency"])
rfm["m_score"] = quintile(rfm["monetary"])
rfm["rfm_score"] = rfm["r_score"] * 100 + rfm["f_score"] * 10 + rfm["m_score"]

rfm["segment"] = np.select(
    [
        (rfm["r_score"] >= 4) & (rfm["f_score"] >= 4),
        (rfm["r_score"] >= 3) & (rfm["f_score"] >= 3),
        (rfm["r_score"] <= 2) & (rfm["f_score"] >= 3),
    ],
    ["Champions", "Loyal", "At Risk"],
    default="Lost / Hibernating",
)

segment_options = ["Champions", "Loyal", "At Risk", "Lost / Hibernating"]
selected_segments = st.sidebar.multiselect(
    "Segments to show", segment_options, default=segment_options
)
visible = rfm[rfm["segment"].isin(selected_segments)]

champions = int((rfm["segment"] == "Champions").sum())
at_risk = int((rfm["segment"] == "At Risk").sum())
col1, col2, col3, col4 = st.columns(4)
col1.metric("Customers", f"{len(rfm):,}")
col2.metric("Champions", f"{champions:,}")
col3.metric("At risk", f"{at_risk:,}")
col4.metric("Average spend", f"${rfm['monetary'].mean():,.0f}")

left, right = st.columns(2)
with left:
    counts = rfm["segment"].value_counts().reindex(segment_options, fill_value=0)
    fig, ax = plt.subplots(figsize=(8, 4))
    sns.barplot(x=counts.index, y=counts.values, hue=counts.index, legend=False, palette="viridis", ax=ax)
    ax.set(title="Customers by segment", xlabel="", ylabel="Customers")
    ax.tick_params(axis="x", rotation=20)
    fig.tight_layout()
    st.pyplot(fig, width="stretch")
    plt.close(fig)

with right:
    fig, ax = plt.subplots(figsize=(8, 4))
    sns.scatterplot(
        data=rfm,
        x="recency",
        y="monetary",
        hue="segment",
        hue_order=segment_options,
        palette="viridis",
        ax=ax,
    )
    ax.set(title="Recency vs. spend", xlabel="Days since last purchase", ylabel="Total spend ($)")
    fig.tight_layout()
    st.pyplot(fig, width="stretch")
    plt.close(fig)

st.subheader("Customer-level scores")
st.dataframe(
    visible.sort_values("monetary", ascending=False),
    hide_index=True,
    width="stretch",
)
st.download_button(
    "Download RFM segments",
    rfm.to_csv(index=False).encode("utf-8"),
    "rfm_segments.csv",
    "text/csv",
)
