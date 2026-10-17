import streamlit as st
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt

st.set_page_config(page_title="Marketing ROI Dashboard", layout="wide")
st.title("Marketing Campaign ROI Dashboard")
st.caption("Track Spend, CAC, ROI and Conversion by Channel")

# Sample data generator
def gen_data():
    rng = np.random.default_rng(7)
    campaigns = ['Google Ads', 'Facebook', 'Instagram', 'Email', 'LinkedIn']
    rows=[]
    for camp in campaigns:
        for i in range(6):
            spend = int(rng.integers(500, 5000))
            clicks = int(rng.integers(200, 5000))
            conv = int(clicks * rng.uniform(0.02, 0.15))
            revenue = conv * int(rng.integers(50, 400))
            rows.append({"campaign": camp, "month": f"2024-{i+1:02d}", "spend": spend, "clicks": clicks, "conversions": conv, "revenue": revenue})
    return pd.DataFrame(rows)

df = gen_data()
df['cac'] = df['spend'] / df['conversions'].replace(0, np.nan)
df['roi'] = (df['revenue'] - df['spend']) / df['spend'] * 100
df['conv_rate'] = df['conversions'] / df['clicks'] * 100

# Filters
st.sidebar.header("Filters")
sel = st.sidebar.multiselect("Campaign", sorted(df['campaign'].unique()), default=sorted(df['campaign'].unique()))
fdf = df[df['campaign'].isin(sel)]

# KPIs
c1,c2,c3,c4 = st.columns(4)
c1.metric("Total Spend", f"${fdf['spend'].sum():,}")
c2.metric("Total Revenue", f"${fdf['revenue'].sum():,}")
c3.metric("Avg ROI", f"{fdf['roi'].mean():.1f}%")
c4.metric("Avg CAC", f"${fdf['cac'].mean():.2f}")

left,right = st.columns(2)
with left:
    monthly = fdf.groupby('month', as_index=False)[['spend','revenue']].sum()
    fig, ax = plt.subplots(figsize=(9,4))
    ax.plot(monthly['month'], monthly['spend'], marker='o', label='Spend')
    ax.plot(monthly['month'], monthly['revenue'], marker='o', label='Revenue')
    ax.set_title("Spend vs Revenue")
    ax.legend()
    plt.xticks(rotation=45)
    st.pyplot(fig)
with right:
    by_camp = fdf.groupby('campaign', as_index=False)[['roi','cac']].mean().sort_values('roi', ascending=False)
    fig, ax = plt.subplots(figsize=(9,4))
    sns.barplot(data=by_camp, x='roi', y='campaign', palette='viridis', ax=ax)
    ax.set_title("ROI by Campaign")
    st.pyplot(fig)

st.subheader("Campaign Performance Table")
st.dataframe(fdf.groupby('campaign', as_index=False).agg(spend=('spend','sum'), revenue=('revenue','sum'), roi=('roi','mean'), cac=('cac','mean')).sort_values('roi', ascending=False), use_container_width=True)
