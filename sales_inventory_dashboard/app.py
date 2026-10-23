import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Sales & Inventory", layout="wide")
st.title("Sales and Inventory Dashboard")
st.caption("Track sales, demand, stock coverage, and a simple three-month forecast.")


@st.cache_data
def generate_sample() -> pd.DataFrame:
    rng = np.random.default_rng(42)
    dates = pd.date_range("2025-01-01", periods=12, freq="MS")
    products = ["Laptop", "Phone", "Tablet", "Headphones", "Monitor"]
    rows = []
    for date in dates:
        for product in products:
            quantity = int(rng.integers(10, 80))
            price = float(rng.integers(25, 500))
            rows.append(
                {
                    "date": date,
                    "product": product,
                    "quantity": quantity,
                    "sales": round(quantity * price, 2),
                    "inventory": int(rng.integers(20, 250)),
                }
            )
    return pd.DataFrame(rows)


def clean_data(file) -> pd.DataFrame:
    frame = pd.read_csv(file)
    frame.columns = (
        frame.columns.str.strip().str.lower().str.replace(" ", "_").str.replace("-", "_")
    )
    aliases = {
        "product_name": "product",
        "item": "product",
        "item_name": "product",
        "order_date": "date",
        "sale_date": "date",
        "units": "quantity",
        "qty": "quantity",
        "revenue": "sales",
        "amount": "sales",
        "stock": "inventory",
        "stock_level": "inventory",
    }
    frame = frame.rename(columns=aliases)
    required = ["date", "product", "quantity", "sales", "inventory"]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(missing))

    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["product"] = frame["product"].astype("string").str.strip()
    for column in ["quantity", "sales", "inventory"]:
        frame[column] = (
            frame[column]
            .astype("string")
            .str.replace("$", "", regex=False)
            .str.replace(",", "", regex=False)
            .str.strip()
        )
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    frame = frame.dropna(subset=["date", "product", "quantity", "sales"])
    frame = frame[(frame["product"] != "") & (frame["quantity"] >= 0) & (frame["sales"] >= 0)]
    frame["inventory"] = frame["inventory"].fillna(0).clip(lower=0)
    if frame.empty:
        raise ValueError("No valid sales rows were found in the uploaded CSV.")
    frame["month"] = frame["date"].dt.to_period("M").dt.to_timestamp()
    return frame


uploaded = st.sidebar.file_uploader(
    "Upload sales CSV",
    type=["csv"],
    help="Required columns: date, product, quantity, sales, inventory",
)
if uploaded:
    try:
        df = clean_data(uploaded)
    except (ValueError, pd.errors.ParserError, UnicodeDecodeError) as exc:
        st.error(str(exc))
        st.stop()
    st.sidebar.caption("Showing results from your uploaded file.")
else:
    df = generate_sample()
    st.info("Showing reproducible sample data. Upload a CSV to explore your own inventory.")

products = sorted(df["product"].dropna().unique().tolist())
selected_products = st.sidebar.multiselect("Products", products, default=products)
filtered = df[df["product"].isin(selected_products)].copy()
if filtered.empty:
    st.warning("Select at least one product to view the dashboard.")
    st.stop()

months_count = max(filtered["month"].nunique(), 1)
monthly_demand = filtered.groupby("product")["quantity"].sum() / months_count
latest_stock = (
    filtered.sort_values("date")
    .groupby("product", as_index=False)
    .tail(1)[["product", "inventory"]]
)
stock = latest_stock.set_index("product")["inventory"]
coverage = stock.div(monthly_demand.replace(0, np.nan))
low_stock_products = int((coverage < 1).sum())

col1, col2, col3, col4 = st.columns(4)
col1.metric("Sales", f"${filtered['sales'].sum():,.0f}")
col2.metric("Units sold", f"{filtered['quantity'].sum():,.0f}")
col3.metric("Average sale", f"${filtered['sales'].mean():,.2f}")
col4.metric("Products under 1 month of stock", f"{low_stock_products:,}")

left, right = st.columns(2)
monthly_sales = filtered.groupby("month", as_index=False)["sales"].sum()
with left:
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(monthly_sales["month"], monthly_sales["sales"], marker="o", color="#2563eb")
    ax.set(title="Monthly sales", xlabel="Month", ylabel="Sales ($)")
    ax.tick_params(axis="x", rotation=35)
    fig.tight_layout()
    st.pyplot(fig, width="stretch")
    plt.close(fig)

with right:
    product_sales = (
        filtered.groupby("product", as_index=False)["sales"]
        .sum()
        .sort_values("sales", ascending=True)
        .tail(10)
    )
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.barh(product_sales["product"], product_sales["sales"], color="#0f766e")
    ax.set(title="Top products by sales", xlabel="Sales ($)", ylabel="")
    fig.tight_layout()
    st.pyplot(fig, width="stretch")
    plt.close(fig)

inventory_table = latest_stock.merge(
    monthly_demand.rename("average_monthly_demand"),
    left_on="product",
    right_index=True,
    how="left",
)
inventory_table["months_of_stock"] = inventory_table["inventory"].div(
    inventory_table["average_monthly_demand"].replace(0, np.nan)
)
inventory_table["status"] = np.select(
    [inventory_table["months_of_stock"] < 1, inventory_table["months_of_stock"] > 3],
    ["Low stock", "Overstocked"],
    default="Healthy",
)

st.subheader("Inventory coverage")
st.dataframe(inventory_table.sort_values("months_of_stock"), hide_index=True, width="stretch")

st.subheader("Three-month sales forecast")
monthly_series = monthly_sales.set_index("month")["sales"].sort_index()
if len(monthly_series) >= 2:
    x = np.arange(len(monthly_series))
    slope, intercept = np.polyfit(x, monthly_series.to_numpy(), 1)
    future_x = np.arange(len(monthly_series), len(monthly_series) + 3)
    forecast = pd.DataFrame(
        {
            "month": pd.date_range(
                monthly_series.index.max() + pd.offsets.MonthBegin(1), periods=3, freq="MS"
            ),
            "forecast_sales": np.maximum(slope * future_x + intercept, 0),
        }
    )
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(monthly_series.index, monthly_series.values, marker="o", label="History")
    ax.plot(forecast["month"], forecast["forecast_sales"], marker="o", linestyle="--", label="Forecast")
    ax.set(ylabel="Sales ($)")
    ax.legend()
    ax.tick_params(axis="x", rotation=35)
    fig.tight_layout()
    st.pyplot(fig, width="stretch")
    plt.close(fig)
    st.dataframe(forecast, hide_index=True, width="stretch")
else:
    st.info("At least two months of sales are needed to calculate a forecast.")

st.download_button(
    "Download cleaned sales data",
    filtered.to_csv(index=False).encode("utf-8"),
    "cleaned_sales_data.csv",
    "text/csv",
)
