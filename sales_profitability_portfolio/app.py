from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Retail Profitability", layout="wide")
st.title("Retail Sales Profitability")
st.caption("Explore profit by location, product, and discount level.")
st.info("This dashboard uses simulated retail transactions. The results are illustrative, not real business findings.")

DATA_FILE = Path(__file__).parent / "data" / "sales.csv"


@st.cache_data
def load_data():
    source = pd.read_csv(DATA_FILE)
    source.columns = source.columns.str.strip().str.lower()
    required = {"order_date", "region", "state", "category", "product_name", "sales", "discount", "profit"}
    missing = required.difference(source.columns)
    if missing:
        raise ValueError("The sales file is missing columns: " + ", ".join(sorted(missing)))

    source["order_date"] = pd.to_datetime(source["order_date"], errors="coerce")
    for column in ["sales", "discount", "profit"]:
        source[column] = pd.to_numeric(source[column], errors="coerce")
    original_rows = len(source)
    clean = source.dropna(subset=["order_date", "sales", "profit"]).copy()
    clean["region"] = clean["region"].fillna("Unknown")
    clean["state"] = clean["state"].fillna("Unknown")
    clean["category"] = clean["category"].fillna("Unknown")
    clean["product_name"] = clean["product_name"].fillna("Unknown")
    clean["discount_band"] = pd.cut(
        clean["discount"],
        bins=[-0.001, 0, 0.1, 0.2, 0.3, 1.0],
        labels=["0%", "1–10%", "11–20%", "21–30%", "Above 30%"],
    )
    clean["discount_band"] = clean["discount_band"].cat.add_categories(["Unknown"]).fillna("Unknown")
    return clean, original_rows


try:
    df, original_rows = load_data()
except (FileNotFoundError, ValueError, pd.errors.ParserError) as exc:
    st.error(f"Project data could not be loaded: {exc}")
    st.stop()

if df.empty:
    st.error("No rows with a valid date, sales, and profit were found.")
    st.stop()

regions = sorted(df["region"].unique().tolist())
categories = sorted(df["category"].unique().tolist())
selected_regions = st.sidebar.multiselect("Regions", regions, default=regions)
selected_categories = st.sidebar.multiselect("Categories", categories, default=categories)

date_values = df["order_date"].dropna().sort_values()
selected_dates = st.sidebar.date_input(
    "Order date range",
    value=(date_values.min().date(), date_values.max().date()),
    min_value=date_values.min().date(),
    max_value=date_values.max().date(),
)
if isinstance(selected_dates, tuple):
    selected_dates = [value for value in selected_dates if value is not None]
    if len(selected_dates) == 2:
        start_date, end_date = selected_dates
    elif len(selected_dates) == 1:
        start_date = end_date = selected_dates[0]
    else:
        start_date, end_date = date_values.min().date(), date_values.max().date()
elif selected_dates is not None:
    start_date = end_date = selected_dates
else:
    start_date, end_date = date_values.min().date(), date_values.max().date()
filtered = df[
    df["region"].isin(selected_regions)
    & df["category"].isin(selected_categories)
    & df["order_date"].dt.date.between(start_date, end_date)
].copy()

if filtered.empty:
    st.warning("No transactions match the selected filters.")
    st.stop()

total_sales = filtered["sales"].sum()
total_profit = filtered["profit"].sum()
profit_margin = total_profit / total_sales if total_sales else np.nan
col1, col2, col3, col4 = st.columns(4)
col1.metric("Sales", f"${total_sales:,.0f}")
col2.metric("Profit", f"${total_profit:,.0f}")
col3.metric("Profit margin", "—" if pd.isna(profit_margin) else f"{profit_margin:.1%}")
col4.metric("Line items", f"{len(filtered):,}")

left, right = st.columns(2)
by_state = (
    filtered.groupby("state", as_index=False)["profit"]
    .sum()
    .sort_values("profit", ascending=True)
    .tail(10)
)
with left:
    fig, ax = plt.subplots(figsize=(8, 4))
    colors = ["#b91c1c" if value < 0 else "#0f766e" for value in by_state["profit"]]
    ax.barh(by_state["state"], by_state["profit"], color=colors)
    ax.axvline(0, color="#64748b", linewidth=0.8)
    ax.set(title="Profit by state (top 10)", xlabel="Profit ($)", ylabel="")
    fig.tight_layout()
    st.pyplot(fig, width="stretch")
    plt.close(fig)

by_product = (
    filtered.groupby("product_name", as_index=False)["profit"]
    .sum()
    .sort_values("profit", ascending=True)
    .tail(10)
)
with right:
    fig, ax = plt.subplots(figsize=(8, 4))
    colors = ["#b91c1c" if value < 0 else "#2563eb" for value in by_product["profit"]]
    ax.barh(by_product["product_name"], by_product["profit"], color=colors)
    ax.axvline(0, color="#64748b", linewidth=0.8)
    ax.set(title="Profit by product (top 10)", xlabel="Profit ($)", ylabel="")
    fig.tight_layout()
    st.pyplot(fig, width="stretch")
    plt.close(fig)

discount_summary = (
    filtered.groupby("discount_band", observed=False, as_index=False)["profit"]
    .mean()
    .dropna(subset=["profit"])
)
st.subheader("Average profit by discount band")
fig, ax = plt.subplots(figsize=(10, 4))
colors = ["#b91c1c" if value < 0 else "#0f766e" for value in discount_summary["profit"]]
ax.bar(discount_summary["discount_band"].astype(str), discount_summary["profit"], color=colors)
ax.axhline(0, color="#64748b", linewidth=0.8)
ax.set(xlabel="Discount", ylabel="Average profit per line ($)")
fig.tight_layout()
st.pyplot(fig, width="stretch")
plt.close(fig)

st.subheader("Filtered transactions")
st.dataframe(filtered.sort_values("profit", ascending=False), hide_index=True, width="stretch")
with st.expander("Data quality"):
    st.write(f"Rows in source file: {original_rows:,}")
    st.write(f"Rows with valid date, sales, and profit: {len(df):,}")
    st.write(f"Rows excluded from the analysis: {original_rows - len(df):,}")
    st.write(f"Rows with missing discount values: {int(df['discount'].isna().sum()):,}")

st.download_button(
    "Download filtered transactions",
    filtered.to_csv(index=False).encode("utf-8"),
    "filtered_profitability.csv",
    "text/csv",
)
