from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
from matplotlib.ticker import PercentFormatter

st.set_page_config(page_title="SaaS Retention & Churn", layout="wide")
st.title("SaaS Revenue and Retention")
st.caption("Monitor recurring revenue, monthly cancellations, and customer cohorts.")
st.info("This dashboard uses a reproducible simulated subscription dataset; results are illustrative.")

DATA_DIR = Path(__file__).parent / "outputs"


@st.cache_data
def load_data():
    mrr = pd.read_csv(DATA_DIR / "mrr_by_month.csv", parse_dates=["month_end"])
    churn = pd.read_csv(DATA_DIR / "monthly_churn.csv", parse_dates=["month_end"])
    cohorts = pd.read_csv(DATA_DIR / "cohort_retention.csv")
    plans = pd.read_csv(DATA_DIR / "plan_summary.csv")
    quality = pd.read_csv(DATA_DIR / "quality_report.csv")
    cohorts["retention_rate"] = pd.to_numeric(cohorts["retention_rate"], errors="coerce")
    return mrr, churn, cohorts, plans, quality


try:
    mrr, churn, cohorts, plans, quality = load_data()
except (FileNotFoundError, pd.errors.ParserError) as exc:
    st.error(f"Dashboard data could not be loaded: {exc}")
    st.stop()

if mrr.empty or churn.empty or cohorts.empty:
    st.error("One or more required project data files are empty.")
    st.stop()

months = mrr["month_end"].dropna().sort_values().tolist()
start_month, end_month = st.sidebar.select_slider(
    "Analysis period",
    options=months,
    value=(months[0], months[-1]),
    format_func=lambda value: value.strftime("%b %Y"),
)
mrr_view = mrr[mrr["month_end"].between(start_month, end_month)].copy()
churn_view = churn[churn["month_end"].between(start_month, end_month)].copy()

latest = mrr_view.iloc[-1]
first = mrr_view.iloc[0]
revenue_change = (latest["mrr_eur"] / first["mrr_eur"] - 1) * 100 if first["mrr_eur"] else np.nan
latest_churn = churn_view.iloc[-1]

col1, col2, col3, col4 = st.columns(4)
col1.metric("Month-end MRR", f"€{latest['mrr_eur']:,.0f}")
col2.metric("Active subscriptions", f"{latest['active_subscriptions']:,.0f}")
col3.metric("MRR change in period", f"{revenue_change:+.1f}%")
col4.metric(
    "Latest monthly churn",
    "—" if pd.isna(latest_churn["monthly_churn_rate"]) else f"{latest_churn['monthly_churn_rate']:.1%}",
    help="Cancellations divided by subscriptions active at the start of the month.",
)

left, right = st.columns(2)
with left:
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(mrr_view["month_end"], mrr_view["mrr_eur"], color="#2563eb", linewidth=2)
    ax.set(title="Month-end recurring revenue", ylabel="MRR (€)", xlabel="")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    st.pyplot(fig, width="stretch")
    plt.close(fig)

with right:
    fig, ax = plt.subplots(figsize=(8, 4))
    rates = churn_view.dropna(subset=["monthly_churn_rate"])
    ax.bar(rates["month_end"], rates["monthly_churn_rate"] * 100, color="#0f766e", width=22)
    ax.set(title="Monthly subscription churn", ylabel="Churn (%)", xlabel="")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    st.pyplot(fig, width="stretch")
    plt.close(fig)

st.subheader("Subscription plan summary")
plan_view = plans.copy()
plan_view["cumulative_cancellation_rate"] = pd.to_numeric(
    plan_view["cumulative_cancellation_rate"], errors="coerce"
)
st.dataframe(
    plan_view.style.format({"cumulative_cancellation_rate": "{:.1%}"}),
    hide_index=True,
    width="stretch",
)

st.subheader("Customer cohort retention")
cohort_months = sorted(cohorts["cohort_month"].dropna().unique())
selected_cohorts = st.multiselect(
    "Cohorts to compare", cohort_months, default=cohort_months[-6:]
)
cohort_view = cohorts[cohorts["cohort_month"].isin(selected_cohorts)]
retention = cohort_view.pivot(
    index="cohort_month", columns="months_since_start", values="retention_rate"
).sort_index()
if retention.empty:
    st.info("Choose one or more cohorts to view retention.")
else:
    fig, ax = plt.subplots(figsize=(12, max(3.5, len(retention) * 0.45)))
    values = retention.to_numpy(dtype=float)
    image = ax.imshow(values, aspect="auto", interpolation="nearest", cmap="YlGnBu", vmin=0, vmax=1)
    ax.set_yticks(np.arange(len(retention.index)), labels=retention.index)
    x_positions = np.arange(0, len(retention.columns), 3)
    ax.set_xticks(x_positions, labels=retention.columns[x_positions])
    ax.set(xlabel="Months since subscription start", ylabel="Cohort month")
    colorbar = fig.colorbar(image, ax=ax, label="Retained (%)")
    colorbar.ax.yaxis.set_major_formatter(PercentFormatter(xmax=1))
    fig.tight_layout()
    st.pyplot(fig, width="stretch")
    plt.close(fig)

with st.expander("Data quality checks"):
    st.dataframe(quality, hide_index=True, width="stretch")

st.download_button(
    "Download monthly revenue and churn",
    mrr_view.merge(churn_view, on="month_end", how="left").to_csv(index=False).encode("utf-8"),
    "saas_revenue_churn.csv",
    "text/csv",
)
