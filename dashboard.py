# dashboard.py — Tru Fru Marketplace Dashboard v2 (Fully Clickable KPI Cards + Wide Dialogs + View Buttons)

import json
from pathlib import Path
import pandas as pd
import streamlit as st

# -----------------------------
# CONFIG
# -----------------------------
st.set_page_config(page_title="TruFru Reseller Analysis", layout="wide")

SUMMARY_FILE = Path("validated_json/trufru_baseprice_payload.json")
PRIMARY = "#0057b8"

# -----------------------------
# CSS
# -----------------------------
sidebar_css = """
<style>
[data-testid="stSidebar"] { background-color: #f4f6fa !important; padding-top: 22px !important; }
[data-testid="stSidebar"] [data-testid="stSidebarNav"] > div:nth-child(1),
[data-testid="stSidebarNav"] div[role="heading"] { display: none !important; }

/* KPI Card Styling */
.kpi-button {
    background: white !important;
    border: 1px solid #e6e6e6 !important;
    border-radius: 16px !important;
    padding: 18px !important;
    box-shadow: 0 4px 14px rgba(0,0,0,0.06) !important;
    height: 150px !important;
    text-align: center !important;
    transition: all 0.2s ease !important;
    cursor: pointer !important;
    color: #444 !important;
}

.kpi-button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 18px rgba(0,0,0,0.12) !important;
}

/* Wide Dialog */
section[data-testid="stDialog"] {
    width: 80vw !important;
    max-width: 1200px !important;
}

section[data-testid="stDialog"] > div {
    width: 100% !important;
}

.badge { padding:6px 10px; border-radius:8px; color:#fff; font-weight:700; display:inline-block; margin:4px; }
</style>
"""
st.markdown(sidebar_css, unsafe_allow_html=True)


# -----------------------------
# Helper Functions
# -----------------------------
def load_json(path: Path):
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def fmt_money(x, decimals=2):
    try:
        return f"${float(x):.{decimals}f}"
    except:
        return "-"


def kpi_card_button(key, title, value, subtitle=""):
    """Clickable KPI card using session state"""

    # Initialize session state
    if f"clicked_{key}" not in st.session_state:
        st.session_state[f"clicked_{key}"] = False

    # Render the card
    st.markdown(
        f"""
<style>
.kpi-card-{key} {{
    background: white;
    border: 1px solid #e6e6e6;
    border-radius: 16px;
    padding: 18px;
    box-shadow: 0 4px 14px rgba(0,0,0,0.06);
    height: 150px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    text-align: center;
    transition: all 0.2s ease;
    cursor: pointer;
    user-select: none;
}}

.kpi-card-{key}:hover {{
    transform: translateY(-2px);
    box-shadow: 0 6px 18px rgba(0,0,0,0.12);
    border-color: #0057b8;
}}

.kpi-card-{key} .title {{
    font-size: 14px;
    font-weight: 700;
    color: #444;
    margin-bottom: 6px;
}}

.kpi-card-{key} .value {{
    font-size: 34px;
    font-weight: 900;
    color: #0057b8;
    line-height: 1.1;
    margin: 8px 0;
}}

.kpi-card-{key} .subtitle {{
    font-size: 12px;
    color: #777;
}}
</style>

<div class="kpi-card-{key}">
    <div class="title">{title}</div>
    <div class="value">{value}</div>
    <div class="subtitle">{subtitle}</div>
</div>
""",
        unsafe_allow_html=True,
    )

    # Use a properly hidden button
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        clicked = st.button("View Details", key=key, type="secondary", width="stretch")

    # Hide the button with CSS
    st.markdown(
        f"""
<style>
/* Hide button completely */
div[data-testid="column"]:has(button[key="{key}"]) {{
    display: none !important;
}}
</style>
""",
        unsafe_allow_html=True,
    )

    return clicked


def price_flag_badge(flag):
    if flag == "Price Gouging":
        return ("Price Gouging", "#ff4d4d")
    if flag == "High Price":
        return ("High Price", "#ff9900")
    if flag == "Slightly High":
        return ("Slightly High", "#ffb84d")
    if flag == "Fair Price":
        return ("Fair Price", "#4caf50")
    return ("-", "#9e9e9e")


def seller_count_badge(count):
    if count == 0:
        return ("0 sellers", "#4caf50")
    if 1 <= count <= 3:
        return (f"{count} sellers", "#ffd400")
    if 4 <= count <= 10:
        return (f"{count} sellers", "#ff8c00")
    return (f"{count} sellers", "#ff4d4d")


def smart_df(df, max_height=400):
    """Auto-fit dataframe height based on row count - eliminates empty rows - index starts at 1"""
    rows = len(df)
    height = min(45 + rows * 35, max_height)
    df_display = df.copy()
    df_display.index = range(1, len(df_display) + 1)
    return st.dataframe(df_display, width="stretch", height=height)


# -----------------------------
# Load Summary JSON
# -----------------------------
summary = load_json(SUMMARY_FILE)
if not summary:
    st.error(f"Summary JSON not found: {SUMMARY_FILE.resolve()}")
    st.info(f"Place the file at: {SUMMARY_FILE.resolve()}")
    st.stop()

# Extract all sections
thresholds = summary.get("thresholds", {})
metrics = summary.get("metrics", {})
comparisons = summary.get("comparisons", []) or []
unique_marketplace_sellers = summary.get("unique_marketplace_sellers", []) or []
products_with_other_sellers_list = (
    summary.get("products_with_other_sellers_list", []) or []
)
top_10_gouged_skus = summary.get("top_10_most_gouged_skus", []) or []
seller_sku_impact = summary.get("seller_sku_impact", []) or []
high_price_seller_analysis = summary.get("high_price_seller_analysis", []) or []
top_violators = summary.get("top_violators", []) or []

product_listings = summary.get("product_listings", [])

# Convert comparisons to DataFrame
df_cmp = pd.DataFrame(comparisons)
if not df_cmp.empty:
    for col in ["base_price", "seller_price", "delta_abs", "delta_pct"]:
        if col in df_cmp.columns:
            df_cmp[col] = pd.to_numeric(df_cmp[col], errors="coerce")
    df_cmp["gouged"] = df_cmp.get("gouged", False).fillna(False).astype(bool)

gouged_df = (
    df_cmp[df_cmp["gouged"] == True].copy() if not df_cmp.empty else pd.DataFrame()
)

total_gouged_impact = (
    float(gouged_df["delta_abs"].sum()) if not gouged_df.empty else 0.0
)
avg_gouged_impact = float(gouged_df["delta_abs"].mean()) if not gouged_df.empty else 0.0

# -----------------------------
# Sidebar Options
# -----------------------------
with st.sidebar:
    pass  # Empty sidebar

# Default values
dollars_no_decimals = False
show_gouged_only = False
money_decimals = 2

# -----------------------------
# Dialog Setup
# -----------------------------
# -----------------------------
# Dialog Setup
# -----------------------------
HAS_DIALOG = hasattr(st, "dialog")

if HAS_DIALOG:

    @st.dialog("All Products", width="large")
    def dlg_all_products(product_listings):
        """Show all products with SKU and Title"""
        st.write(f"Total Products: {len(product_listings)}")
        st.markdown("---")

        all_products_df = pd.DataFrame(
            [
                {
                    "SKU": p.get("asins", [""])[0],
                    "Title": p.get("product_name", ""),
                }
                for p in product_listings
            ]
        )
        smart_df(all_products_df, max_height=600)

    @st.dialog("Products With Marketplace Sellers", width="large")
    def dlg_products_with_market(products_list):
        """Show only products that have marketplace sellers"""
        if not products_list:
            st.info("No products with marketplace sellers found.")
            return

        st.write(f"Products with 3rd party sellers: {len(products_list)}")
        st.markdown("---")
        smart_df(pd.DataFrame(products_list), max_height=600)

    @st.dialog("Total Listings Compared", width="large")
    def dlg_total_listings(df_cmp):
        st.write(f"Total Listings Compared: {len(df_cmp)}")
        if df_cmp.empty:
            st.info("No comparison data.")
            return
        smart_df(df_cmp, max_height=600)

    @st.dialog("Gouged Listings", width="large")
    def dlg_gouged_listings(gouged_df):
        st.write(f"Gouged Listings: {len(gouged_df)}")
        if gouged_df.empty:
            st.info("No gouged listings found.")
            return
        smart_df(gouged_df, max_height=600)

    @st.dialog("Total Revenue Impact", width="large")
    def dlg_total_impact(gouged_df):
        if gouged_df.empty:
            st.info("No gouged listings found.")
            return

        st.write(f"**Total Gouged Listings:** {len(gouged_df)}")
        st.write(f"**Total Impact:** {fmt_money(gouged_df['delta_abs'].sum(), 2)}")
        st.markdown("---")
        smart_df(
            gouged_df[["asin", "title", "seller_name", "delta_abs", "delta_pct"]],
            max_height=600,
        )

    @st.dialog("Pricing Impact Summary", width="large")
    def dlg_avg_stats(avg_pct_all: float, avg_abs_all: float, avg_pct_flagged: float):
        st.markdown("### Pricing Impact Summary")
        st.caption(
            "This summary compares marketplace seller prices to the **Amazon/Base reference price**. "
            "It answers: **On average, how much higher are sellers pricing?**"
        )

        c1, c2, c3 = st.columns(3)

        with c1:
            st.metric(
                "Typical % higher (overall)",
                f"{avg_pct_all:.2f}%",
                help="Average percent higher than the Amazon/Base reference across all listings."
            )

        with c2:
            st.metric(
                "Typical $ higher (overall)",
                fmt_money(avg_abs_all, 2),
                help="Average dollar amount higher than the Amazon/Base reference across all listings."
            )

        with c3:
            st.metric(
                "Typical % higher (flagged listings)",
                f"{avg_pct_flagged:.2f}%",
                help="Average percent higher than the Amazon/Base reference for listings flagged as potential violations."
            )

        st.divider()
        st.markdown(
            "**How to read this:** If it shows **1.00%**, it means sellers are pricing about **1% above** the Amazon/Base reference on average."
        )

# -----------------------------
# Header
# -----------------------------

# Banner image
st.image("trufru.jpeg", width="stretch")

# Title
st.markdown(
    f"<h1 style='text-align:center;color:{PRIMARY};margin-bottom:0;'>TruFru Marketplace Dashboard</h1>",
    unsafe_allow_html=True,
)
# st.caption("Click view to drill down.")

# -----------------------------
# KPI Row (FULLY CLICKABLE CARDS)
# -----------------------------
products_total = metrics.get("products_total", "-")
products_with_other = metrics.get("products_with_other_sellers", "-")
comparisons_count = metrics.get("listing_comparisons_count", "-")
gouged_count = metrics.get("gouged_listings_count", "-")
avg_pct_all = metrics.get("avg_overprice_pct_all", 0.0)
avg_abs_all = metrics.get("avg_overprice_abs_all", 0.0)
avg_pct_gouged_only = metrics.get("avg_overprice_pct_gouged_only", 0.0)
unique_mkt_seller_count = len(unique_marketplace_sellers)

st.markdown("### KPIs")
c1, c2, c3, c4, c5, c6 = st.columns(6)

with c1:
    if kpi_card_button(
        "kpi_products",
        "Products",
        str(products_total),
        "Total SKUs in catalog",
    ):
        if HAS_DIALOG:
            dlg_all_products(product_listings)  # Show ALL 36 products

with c2:
    if kpi_card_button(
        "kpi_marketplace_products",
        "With Marketplace Sellers",
        str(products_with_other),
        "SKUs sold by 3rd party sellers",
    ):
        if HAS_DIALOG:
            dlg_products_with_market(products_with_other_sellers_list)  # Show only 7

with c3:
    if kpi_card_button(
        "kpi_compared",
        "Listings Compared",
        str(comparisons_count),
        "Total price comparisons analyzed",
    ):
        if HAS_DIALOG:
            dlg_total_listings(df_cmp)  # Updated function name

with c4:
    if kpi_card_button(
        "kpi_gouged",
        "Gouged Listings",
        str(gouged_count),
        "Listings exceeding price thresholds",
    ):
        if HAS_DIALOG:
            dlg_gouged_listings(gouged_df)

with c5:
    if kpi_card_button(
        "kpi_total_impact",
        "Total $ Impact",
        fmt_money(total_gouged_impact, money_decimals),
        "Combined revenue loss from gouging",
    ):
        if HAS_DIALOG:
            dlg_total_impact(gouged_df)  # Updated function

with c6:
    if kpi_card_button(
        "kpi_avg_impact",
        "Avg $ Impact",
        fmt_money(avg_gouged_impact, money_decimals),
        "Average price markup per gouged listing",
    ):
        if HAS_DIALOG:
            dlg_avg_stats(avg_pct_all, avg_abs_all, avg_pct_gouged_only)

st.markdown("---")

# -----------------------------
# Main Tabs
# -----------------------------
tab_insights, tab_charts, tab_explorer = st.tabs(
    [" Marketplace Insights", " Charts & Insights", " Product Listing Explorer"]
)

# -----------------------------
# TAB 1: Marketplace Insights
# -----------------------------

with tab_insights:
    st.markdown("## Marketplace Insights")

    # Row 1: Marketplace Sellers + Top Violators (side by side)
    left_col, right_col = st.columns(2)

    with left_col:
        st.markdown("###  Marketplace Sellers")
        smart_df(pd.DataFrame({"seller_name": unique_marketplace_sellers}))

    with right_col:
        st.markdown("###  Top Violators")
        if top_violators:
            tv_df = pd.DataFrame(
                [
                    {
                        "Seller Name": row["seller_name"],
                        "Gouged Listings": row["gouged_listings"],
                        "Avg Overprice %": f"{row['avg_overprice_pct']}%",
                        "Gouged SKUs": row.get("asins", ""),
                    }
                    for row in top_violators
                ]
            )

            tv_df.index = range(1, len(tv_df) + 1)
            st.dataframe(tv_df, width="stretch", height=min(45 + len(tv_df) * 35, 400))
        else:
            st.info("No violators found.")

    st.markdown("---")

    # Row 2: Top 10 Most Gouged SKUs (full width)
    st.markdown("###  Top 5 Most Gouged SKUs with Seller Breakdown")

    if top_10_gouged_skus:
        # Flatten the data for table view
        gouged_table = []
        for idx, sku in enumerate(top_10_gouged_skus, 1):
            for seller in sku["gouging_sellers"]:
                gouged_table.append(
                    {
                        "Rank": idx,
                        "SKU": sku["asin"],
                        "Title": sku["title"],
                        "Base Seller": sku["base_seller"],
                        "Base Price": fmt_money(sku["base_price"], money_decimals),
                        "Gouging Seller": seller["seller_name"],
                        "Seller Price": fmt_money(
                            seller["seller_price"], money_decimals
                        ),
                        "Price Δ ($)": fmt_money(seller["delta_abs"], money_decimals),
                        "Price Δ (%)": f"{seller['delta_pct']:.2f}%",
                    }
                )

        gouged_df_table = pd.DataFrame(gouged_table)
        smart_df(gouged_df_table, max_height=600)
    else:
        st.info("No gouged SKUs found.")

    st.markdown("---")

    # Row 3: Seller Risk Analysis (side by side)
    st.markdown("### Seller Risk Analysis")

    left, right = st.columns(2)

    with left:
        st.markdown("#### High Price Seller Analysis")
        if high_price_seller_analysis:
            hp_df = pd.DataFrame(
                [
                    {
                        "Seller Name": row["seller_name"],
                        "Total SKUs": row["total_skus"],
                        "Overpriced SKUs Count": row["overpriced_skus"],
                        "Avg Δ %": f"{row['avg_delta_percent']}%",
                        "Overpriced SKUs": row.get("asins", ""),
                    }
                    for row in high_price_seller_analysis
                ]
            )

            hp_df.index = range(1, len(hp_df) + 1)
            st.dataframe(hp_df, width="stretch", height=min(45 + len(hp_df) * 35, 400))
        else:
            st.info("No high price sellers found.")

    with right:
        st.markdown("#### Seller SKU Impact")
        if seller_sku_impact:
            si_df = pd.DataFrame(
                [
                    {
                        "Seller Name": row["seller_name"],
                        "SKU Count": row["sku_count"],
                        "Gouged SKUs": row.get("asins", ""),
                    }
                    for row in seller_sku_impact
                ]
            )

            si_df.index = range(1, len(si_df) + 1)
            st.dataframe(si_df, width="stretch", height=min(45 + len(si_df) * 35, 400))
        else:
            st.info("No seller SKU impact data.")



# -----------------------------
# TAB 2: Charts & Insights
# -----------------------------
# -----------------------------
# TAB 2: Charts & Insights
# -----------------------------
# -----------------------------
# TAB 2: Charts & Insights
# -----------------------------
# -----------------------------
# TAB 2: Charts & Insights
# -----------------------------
# -----------------------------
# TAB 2: Charts & Insights
# -----------------------------
# with tab_charts:
#     st.markdown("## 📈 Charts & Insights")

#     # -----------------------------
#     # Scope (hide toggle under Advanced)
#     # -----------------------------
#     include_all = False
#     with st.expander("Advanced (internal)", expanded=False):
#         include_all = st.checkbox(
#             "Show ALL listings (includes non-violations)",
#             value=False,
#             help="Client view should normally stay on Gouged Listings Only."
#         )

#     df_chart = df_cmp.copy() if include_all else gouged_df.copy()
#     chart_label = "All Listings" if include_all else "Gouged Listings Only"

#     if df_chart.empty:
#         st.warning("No data available for charting.")
#         st.stop()

#     st.info(f"**Scope:** {chart_label} ({len(df_chart)} rows)")

#     # -----------------------------
#     # Plotly
#     # -----------------------------
#     try:
#         import plotly.express as px
#         import plotly.graph_objects as go
#         use_plotly = True
#     except ImportError:
#         use_plotly = False
#         st.warning("Plotly not available. Install with: pip install plotly")

#     # -----------------------------
#     # price_flag (derive only if missing)
#     # -----------------------------
#     if "price_flag" not in df_chart.columns:
#         def classify_severity(row):
#             # row.get guards against missing keys
#             gouged = bool(row.get("gouged", False))
#             delta_pct = row.get("delta_pct", 0) or 0

#             if gouged:
#                 return "Price Gouging"
#             if delta_pct >= 15:
#                 return "High Price"
#             if delta_pct >= 10:
#                 return "Slightly High"
#             return "Fair Price"

#         # safe copy to avoid SettingWithCopy warnings
#         df_chart = df_chart.copy()
#         df_chart["price_flag"] = df_chart.apply(classify_severity, axis=1)

#     # (keep the rest of your chart sections below as-is)
# -----------------------------
# TAB 2: Charts & Insights
# -----------------------------
# -----------------------------
# TAB 2: Charts & Insights
# -----------------------------
with tab_charts:
    st.markdown("## Charts & Insights")
    st.caption("Visual summary of price-gap drivers, concentration, and seller-by-product patterns.")

    # ✅ Client-safe default: always gouged only (no UI filter)
    df_chart = gouged_df.copy()
    chart_label = "Gouged Listings Only"

    if df_chart.empty:
        st.warning("No data available for charting.")
        st.stop()

    # -----------------------------
    # Plotly
    # -----------------------------
    try:
        import plotly.express as px
        import plotly.graph_objects as go
        use_plotly = True
    except ImportError:
        use_plotly = False
        st.warning("Plotly not available. Install with: pip install plotly")

    # -----------------------------
    # price_flag (derive only if missing)
    # -----------------------------
    if "price_flag" not in df_chart.columns:
        def classify_severity(row):
            gouged = bool(row.get("gouged", False))
            delta_pct = row.get("delta_pct", 0) or 0

            if gouged:
                return "Price Gouging"
            if delta_pct >= 15:
                return "High Price"
            if delta_pct >= 10:
                return "Slightly High"
            return "Fair Price"

        df_chart = df_chart.copy()
        df_chart["price_flag"] = df_chart.apply(classify_severity, axis=1)

    # -----------------------------
    # SECTION 1: Exposure Drivers
    # -----------------------------
    st.markdown("---")
    st.markdown("### Exposure Drivers")
    st.caption("Shows where the total overcharge dollars are coming from.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Highest-Impact Products (by $ Exposure)")
        st.caption("Products ranked by total overcharge dollars; colors indicate severity level.")
        
        # Group by SKU and severity
        sku_severity = (
            df_chart
            .groupby(['asin', 'title', 'price_flag'], as_index=False)
            .agg(exposure_usd=('delta_abs', 'sum'))
        )
        # Get top 10 SKUs by total exposure
        top_skus = (
            sku_severity
            .groupby(['asin', 'title'], as_index=False)
            .agg(total_exposure=('exposure_usd', 'sum'))
            .sort_values('total_exposure', ascending=False)
            .head(100)
        )
        sku_severity_top = sku_severity[sku_severity['asin'].isin(top_skus['asin'])]
        sku_severity_top['sku_label'] = sku_severity_top['asin'] + ' - ' + sku_severity_top['title'].str[:25] + '...'
        
        # Define color map for severity
        color_map = {
            'Fair Price': '#4caf50',
            'Slightly High': '#ffb84d',
            'High Price': '#ff9900',
            'Price Gouging': '#ff4d4d'
        }
        
        if use_plotly:
            fig1 = px.bar(
                sku_severity_top,
                x='exposure_usd',
                y='sku_label',
                color='price_flag',
                orientation='h',
                labels={'exposure_usd': 'Exposure ($)', 'sku_label': 'Product', 'price_flag': 'Severity'},
                title='Highest-Impact Products (by $ Exposure)',
                color_discrete_map=color_map,
                category_orders={'price_flag': ['Fair Price', 'Slightly High', 'High Price', 'Price Gouging']}
            )
            fig1.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig1, use_container_width=True)
        else:
            st.bar_chart(sku_severity_top.pivot_table(index='sku_label', columns='price_flag', values='exposure_usd', fill_value=0))
    
    with col2:
        st.markdown("#### Highest-Impact Sellers (by $ Exposure)")
        st.caption("Sellers ranked by total overcharge dollars; labels show number of products impacted.")
        
        # Group by seller
        seller_impact = (
            df_chart
            .groupby('seller_name', as_index=False)
            .agg(
                exposure_usd=('delta_abs', 'sum'),
                sku_count=('asin', 'nunique'),
                listing_count=('asin', 'count')
            )
            .sort_values('exposure_usd', ascending=False)
            .head(10)
        )
        
        if use_plotly:
            fig2 = go.Figure()
            # Bar for exposure
            fig2.add_trace(go.Bar(
                x=seller_impact['exposure_usd'],
                y=seller_impact['seller_name'],
                orientation='h',
                name='Exposure ($)',
                marker_color='#ff4d4d',
                text=seller_impact['sku_count'].apply(lambda x: f"{x} products"),
                textposition='outside'
            ))
            fig2.update_layout(
                title='Highest-Impact Sellers (by $ Exposure)',
                xaxis_title='Total Exposure ($)',
                yaxis_title='Seller',
                yaxis={'categoryorder':'total ascending'},
                showlegend=False
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.bar_chart(seller_impact.set_index('seller_name')['exposure_usd'])
    
    # -----------------------------
    # SECTION 2: Concentration Overview
    # -----------------------------
    st.markdown("---")
    st.markdown("### Concentration Overview")
    st.caption("Shows whether exposure is driven by a small set of products/sellers or spread across many.")

    col1, col2 = st.columns(2)

    # -----------------------------
    # PARETO BY PRODUCT
    # -----------------------------
    with col1:
        st.markdown("#### Product Exposure Concentration (Exposure + Running Share)")
        st.caption("Bars show exposure per product. The line shows the running share of total exposure from highest to lowest.")

        sku_pareto = (
            df_chart
            .groupby(["asin", "title"], as_index=False)
            .agg(exposure=("delta_abs", "sum"))
            .sort_values("exposure", ascending=False)
        )

        if sku_pareto.empty or sku_pareto["exposure"].sum() <= 0:
            st.info("Not enough exposure data to build product concentration.")
        else:
            sku_pareto["running_share_pct"] = 100 * sku_pareto["exposure"].cumsum() / sku_pareto["exposure"].sum()
            sku_pareto["rank"] = range(1, len(sku_pareto) + 1)
            sku_pareto["sku_label"] = sku_pareto["asin"].astype(str) + " — " + sku_pareto["title"].fillna("").str.slice(0, 45)

            # ✅ FIX: Correct calculation for 80% threshold
            skus_for_80 = (sku_pareto["running_share_pct"] <= 80).sum()
            if skus_for_80 == 0:  # Edge case: first SKU > 80%
                skus_for_80 = 1
            
            total_skus = len(sku_pareto)

            # show top 20 only (readable)
            sku_plot = sku_pareto.head(min(20, total_skus)).copy()

            st.metric(
                "80% of exposure comes from",
                f"{skus_for_80} products",
                f"out of {total_skus} total products"
            )

            if use_plotly:
                fig3 = go.Figure()

                # bars = exposure
                fig3.add_trace(go.Bar(
                    x=sku_plot["sku_label"],
                    y=sku_plot["exposure"],
                    name="Exposure ($)",
                    marker_color="lightblue",
                    hovertemplate="<b>%{x}</b><br>Exposure: $%{y:.2f}<extra></extra>"
                ))

                # line = running share
                fig3.add_trace(go.Scatter(
                    x=sku_plot["sku_label"],
                    y=sku_plot["running_share_pct"],
                    name="Running Share (%)",
                    yaxis="y2",
                    mode="lines+markers",
                    line=dict(color="#0057b8", width=3),
                    hovertemplate="<b>%{x}</b><br>Running Share: %{y:.1f}%<extra></extra>"
                ))

                # 80% line
                fig3.add_shape(
                    type="line",
                    x0=-0.5, x1=len(sku_plot)-0.5,
                    y0=80, y1=80,
                    yref="y2",
                    line=dict(color="red", width=2, dash="dash")
                )
                fig3.add_annotation(
                    x=len(sku_plot)-1,
                    y=80,
                    yref="y2",
                    text="80% threshold",
                    showarrow=False,
                    font=dict(color="red"),
                    bgcolor="white"
                )

                fig3.update_layout(
                    title="Product Exposure Concentration",
                    xaxis_title="Product (sorted by highest exposure)",
                    yaxis=dict(title="Exposure ($)"),
                    yaxis2=dict(title="Running Share (%)", overlaying="y", side="right", range=[0, 100]),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
                    height=520
                )
                fig3.update_xaxes(tickangle=35)
                st.plotly_chart(fig3, use_container_width=True)
            else:
                st.bar_chart(sku_plot.set_index("sku_label")["exposure"])

            # ✅ Display as formatted list
            st.markdown("**Products driving approximately 80% of exposure:**")
            top_sku_list = sku_pareto.head(skus_for_80)[["asin", "title", "exposure"]].copy()
            
            for idx, row in top_sku_list.iterrows():
                st.markdown(f"- **{row['asin']}** — {row['title'][:60]} (${row['exposure']:.2f})")

    # -----------------------------
    # PARETO BY SELLER
    # -----------------------------
    with col2:
        st.markdown("#### Seller Exposure Concentration (Exposure + Running Share)")
        st.caption("Bars show exposure per seller. The line shows the running share of total exposure from highest to lowest.")

        seller_pareto = (
            df_chart
            .groupby("seller_name", as_index=False)
            .agg(exposure=("delta_abs", "sum"))
            .sort_values("exposure", ascending=False)
        )

        if seller_pareto.empty or seller_pareto["exposure"].sum() <= 0:
            st.info("Not enough exposure data to build seller concentration.")
        else:
            seller_pareto["running_share_pct"] = 100 * seller_pareto["exposure"].cumsum() / seller_pareto["exposure"].sum()
            seller_pareto["rank"] = range(1, len(seller_pareto) + 1)

            # ✅ FIX: Correct calculation for 80% threshold
            sellers_for_80 = (seller_pareto["running_share_pct"] <= 80).sum()
            if sellers_for_80 == 0:  # Edge case: first seller > 80%
                sellers_for_80 = 1
            
            total_sellers = len(seller_pareto)

            seller_plot = seller_pareto.head(min(20, total_sellers)).copy()

            st.metric(
                "80% of exposure comes from",
                f"{sellers_for_80} sellers",
                f"out of {total_sellers} total sellers"
            )

            if use_plotly:
                fig4 = go.Figure()

                fig4.add_trace(go.Bar(
                    x=seller_plot["seller_name"],
                    y=seller_plot["exposure"],
                    name="Exposure ($)",
                    marker_color="lightcoral",
                    hovertemplate="<b>%{x}</b><br>Exposure: $%{y:.2f}<extra></extra>"
                ))

                fig4.add_trace(go.Scatter(
                    x=seller_plot["seller_name"],
                    y=seller_plot["running_share_pct"],
                    name="Running Share (%)",
                    yaxis="y2",
                    mode="lines+markers",
                    line=dict(color="#ff4d4d", width=3),
                    hovertemplate="<b>%{x}</b><br>Running Share: %{y:.1f}%<extra></extra>"
                ))

                fig4.add_shape(
                    type="line",
                    x0=-0.5, x1=len(seller_plot)-0.5,
                    y0=80, y1=80,
                    yref="y2",
                    line=dict(color="red", width=2, dash="dash")
                )
                fig4.add_annotation(
                    x=len(seller_plot)-1,
                    y=80,
                    yref="y2",
                    text="80% threshold",
                    showarrow=False,
                    font=dict(color="red"),
                    bgcolor="white"
                )

                fig4.update_layout(
                    title="Seller Exposure Concentration",
                    xaxis_title="Seller (sorted by highest exposure)",
                    yaxis=dict(title="Exposure ($)"),
                    yaxis2=dict(title="Running Share (%)", overlaying="y", side="right", range=[0, 100]),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
                    height=520
                )
                fig4.update_xaxes(tickangle=35)
                st.plotly_chart(fig4, use_container_width=True)
            else:
                st.bar_chart(seller_plot.set_index("seller_name")["exposure"])

            # ✅ Display as formatted list
            st.markdown("**Sellers driving approximately 80% of exposure:**")
            top_seller_list = seller_pareto.head(sellers_for_80)[["seller_name", "exposure"]].copy()
            
            for idx, row in top_seller_list.iterrows():
                st.markdown(f"- **{row['seller_name']}** (${row['exposure']:.2f})")

    # -----------------------------
    # SECTION 3: SKU × Seller Price Gap Heatmap
    # -----------------------------
    st.markdown("---")
    st.markdown("### SKU × Seller Price Gap Heatmap")
    st.caption("Matrix of average % overcharge vs base/Amazon price. Blank cells mean no listing; N/A means missing price.")

    # ✅ Filter ONLY for heatmap (does not affect other charts)
    heatmap_scope = st.radio(
        "Heatmap scope",
        ["Gouged SKUs only", "All SKUs"],
        index=0,
        horizontal=True,
        help="This filter only changes the heatmap display."
    )

    # -----------------------------
    # Source data for heatmap
    # -----------------------------
    df_heat = gouged_df.copy() if heatmap_scope == "Gouged SKUs only" else df_cmp.copy()

    if df_heat.empty:
        st.info("No data available for the selected heatmap scope.")
    else:
        import numpy as np
        import plotly.graph_objects as go

        # -----------------------------
        # Build FULL catalog SKU list
        # -----------------------------
        catalog_rows = []
        for p in (product_listings or []):
            title = (p.get("product_name") or "").strip()
            for asin in (p.get("asins") or []):
                catalog_rows.append({"asin": str(asin).strip(), "title": title})

        catalog_df = pd.DataFrame(catalog_rows)
        if not catalog_df.empty:
            catalog_df = catalog_df.drop_duplicates(subset=["asin"], keep="first")
        else:
            catalog_df = (
                df_cmp[["asin", "title"]].dropna().astype(str).drop_duplicates(subset=["asin"])
                if not df_cmp.empty else pd.DataFrame(columns=["asin", "title"])
            )

        # -----------------------------
        # SKU keep list
        # -----------------------------
        if heatmap_scope == "All SKUs":
            sku_keep = catalog_df.copy()
        else:
            sku_keep = (
                df_heat.groupby(["asin", "title"], as_index=False)
                .agg(total_exposure=("delta_abs", "sum"))
                .sort_values("total_exposure", ascending=False)[["asin", "title"]]
            )

        if sku_keep.empty:
            st.info("No SKUs available for this heatmap scope.")
        else:
            # -----------------------------
            # Normalize seller strings
            # -----------------------------
            df_heat = df_heat.copy()
            df_heat["asin"] = df_heat["asin"].astype(str).str.strip()
            df_heat["title"] = df_heat["title"].fillna("").astype(str).str.strip()
            df_heat["seller_name"] = df_heat["seller_name"].astype("string")
            df_heat["seller_name"] = df_heat["seller_name"].str.strip()

            # Show ALL sellers from selected scope
            df_for_sellers = df_heat.dropna(subset=["seller_name"]).copy()
            seller_keep = sorted(df_for_sellers["seller_name"].astype(str).unique().tolist())

            # -----------------------------
            # LEFT JOIN: keep all SKUs
            # -----------------------------
            df_hm = sku_keep.merge(df_heat, on=["asin", "title"], how="left")
            df_hm = df_hm[(df_hm["seller_name"].isna()) | (df_hm["seller_name"].isin(seller_keep))].copy()

            # -----------------------------
            # Base price per SKU
            # -----------------------------
            base_source = df_cmp if (heatmap_scope == "All SKUs" and not df_cmp.empty) else df_heat

            sku_base = (
                base_source.groupby(["asin", "title"], as_index=False)
                .agg(
                    base_price=("base_price", "min"),
                    base_seller=("base_seller", "first"),
                )
            )

            sku_base_all = sku_keep.merge(sku_base, on=["asin", "title"], how="left")

            # -----------------------------
            # Seller stats per SKU × Seller
            # -----------------------------
            seller_stats = (
                df_hm.dropna(subset=["seller_name"])
                .groupby(["asin", "title", "seller_name"], as_index=False)
                .agg(
                    avg_delta_pct=("delta_pct", "mean"),
                    avg_delta_abs=("delta_abs", "mean"),
                    avg_seller_price=("seller_price", "mean"),
                )
                .merge(sku_base_all, on=["asin", "title"], how="left")
            )

            # -----------------------------
            # Add baseline column
            # -----------------------------
            baseline_label = "Amazon/Base (0%)"
            base_rows = (
                sku_base_all.assign(
                    seller_name=baseline_label,
                    avg_delta_pct=0.0,
                    avg_delta_abs=0.0,
                    avg_seller_price=lambda d: d["base_price"],
                )
            )

            seller_stats = pd.concat([seller_stats, base_rows], ignore_index=True)

            # -----------------------------
            # Labels / orders
            # -----------------------------
            seller_order = [baseline_label] + seller_keep

            seller_stats["sku_label"] = (
                seller_stats["asin"].astype(str)
                + " — "
                + seller_stats["title"].fillna("").astype(str).str.slice(0, 60)
            )

            if heatmap_scope == "All SKUs":
                sku_order = (
                    sku_keep.assign(
                        sku_label=lambda d: d["asin"].astype(str) + " — " + d["title"].fillna("").astype(str).str.slice(0, 60)
                    )
                    .sort_values(["title", "asin"], ascending=True)["sku_label"]
                    .tolist()
                )
            else:
                sku_rank = (
                    df_heat.groupby(["asin", "title"], as_index=False)
                    .agg(total_exposure=("delta_abs", "sum"))
                    .sort_values("total_exposure", ascending=False)
                )
                sku_order = (
                    sku_rank.merge(sku_keep, on=["asin", "title"], how="inner")
                    .assign(sku_label=lambda d: d["asin"].astype(str) + " — " + d["title"].fillna("").astype(str).str.slice(0, 60))
                    .sort_values("total_exposure", ascending=False)["sku_label"]
                    .tolist()
                )

            # -----------------------------
            # Pivot matrices
            # -----------------------------
            z = (
                seller_stats.pivot_table(index="sku_label", columns="seller_name", values="avg_delta_pct", aggfunc="mean")
                .reindex(index=sku_order, columns=seller_order)
            )

            base_price_mat = (
                seller_stats.pivot_table(index="sku_label", columns="seller_name", values="base_price", aggfunc="first")
                .reindex(index=sku_order, columns=seller_order)
            )

            seller_price_mat = (
                seller_stats.pivot_table(index="sku_label", columns="seller_name", values="avg_seller_price", aggfunc="first")
                .reindex(index=sku_order, columns=seller_order)
            )

            delta_abs_mat = (
                seller_stats.pivot_table(index="sku_label", columns="seller_name", values="avg_delta_abs", aggfunc="mean")
                .reindex(index=sku_order, columns=seller_order)
            )

            # -----------------------------
            # Format hover data
            # -----------------------------
            def _to_float_np(df):
                return df.to_numpy(dtype=float)

            z_np = _to_float_np(z)
            base_np = _to_float_np(base_price_mat)
            seller_np = _to_float_np(seller_price_mat)
            abs_np = _to_float_np(delta_abs_mat)

            def _fmt_money(a: np.ndarray) -> np.ndarray:
                out = np.empty(a.shape, dtype=object)
                it = np.nditer(a, flags=["multi_index"])
                for v in it:
                    idx = it.multi_index
                    val = float(v)
                    out[idx] = f"${val:.2f}" if np.isfinite(val) else "N/A"
                return out

            def _fmt_pct(a: np.ndarray) -> np.ndarray:
                out = np.empty(a.shape, dtype=object)
                it = np.nditer(a, flags=["multi_index"])
                for v in it:
                    idx = it.multi_index
                    val = float(v)
                    out[idx] = f"{val:.1f}%" if np.isfinite(val) else "N/A"
                return out

            base_str = _fmt_money(base_np)
            seller_str = _fmt_money(seller_np)
            abs_str = _fmt_money(abs_np)
            pct_str = _fmt_pct(z_np)

            customdata = np.dstack([base_str, seller_str, abs_str, pct_str])

            # -----------------------------
            # Plot heatmap
            # -----------------------------
            if use_plotly:
                fig_hm = go.Figure(
                    data=go.Heatmap(
                        z=z_np,
                        x=list(z.columns),
                        y=list(z.index),
                        customdata=customdata,
                        colorscale="Reds",
                        colorbar=dict(title="Avg Overcharge %"),
                        hovertemplate=(
                            "<b>%{y}</b><br>"
                            "Seller: %{x}<br>"
                            "Base Price: %{customdata[0]}<br>"
                            "Seller Price: %{customdata[1]}<br>"
                            "Overcharge ($): %{customdata[2]}<br>"
                            "Overcharge (%): %{customdata[3]}<extra></extra>"
                        ),
                    )
                )

                fig_hm.update_layout(
                    title="SKU × Seller Price Gap Heatmap",
                    xaxis_title="Seller",
                    yaxis_title="Product (SKU)",
                    height=820 if heatmap_scope == "All SKUs" else 700,
                )
                fig_hm.update_xaxes(tickangle=35)

                st.plotly_chart(fig_hm, use_container_width=True)
            else:
                st.warning("Plotly not available — heatmap requires Plotly.")

    # -----------------------------
    # SECTION 4: Evidence & Action List
    # -----------------------------
    st.markdown("---")
    st.markdown("#### Product Impact Summary")
    st.caption("Each row is one product (SKU). Shows how many sellers are involved, total overcharge dollars, and the worst overcharge %.")
    
    sku_summary = (
        df_chart
        .groupby(['asin', 'title'], as_index=False)
        .agg(
            gouged_seller_count=('seller_name', 'nunique'),
            gouged_listings=('seller_name', 'size'),
            exposure_usd=('delta_abs', 'sum'),
            worst_delta_pct=('delta_pct', 'max')
        )
        .sort_values('exposure_usd', ascending=False)
        .head(10)
    )
    sku_summary.columns = ['SKU', 'Title', 'Gouged Seller Count', 'Gouged Listings', 'Exposure ($)', 'Worst Delta %']
    sku_summary['Exposure ($)'] = sku_summary['Exposure ($)'].apply(lambda x: fmt_money(x, 2))
    sku_summary['Worst Delta %'] = sku_summary['Worst Delta %'].apply(lambda x: f"{x:.2f}%")
    smart_df(sku_summary, max_height=400)


        

# -----------------------------
# TAB 3: Product Listing Explorer
# -----------------------------
# -----------------------------
# TAB 3: Product Listing Explorer
# -----------------------------
with tab_explorer:
    st.markdown("## Product Listing Explorer")

    st.markdown("### Filters")

    c1, c2 = st.columns(2)

    with c1:
        all_price_flags = ["Fair Price", "High Price", "Slightly High", "Price Gouging"]
        price_flag_filter = st.multiselect("Price Flags", all_price_flags)

    with c2:
        seller_filter = st.selectbox(
            "Seller", ["All Sellers"] + unique_marketplace_sellers
        )

    c3, c4, c5 = st.columns(3)

    with c3:
        search_query = (
            st.text_input(
                "Search products by name / flavor / SKU",
                placeholder="Type to search...",
            )
            .lower()
            .strip()
        )

    with c4:
        sort_choice = st.selectbox(
            "Sort By",
            [
                "Default",
                "Product Name (A → Z)",
                "Product Name (Z → A)",
                "Marketplace Sellers (High → Low)",
                "Marketplace Sellers (Low → High)",
            ],
        )

    with c5:
        marketplace_filter = st.selectbox(
            "Marketplace filter",
            [
                "All SKUs",
                "Only with marketplace sellers",
                "Only without marketplace sellers",
            ],
        )

    st.markdown("---")

    # Apply filters
    filtered_products = product_listings.copy()

    if search_query:
        filtered_products = [
            p
            for p in filtered_products
            if search_query in (p.get("product_name") or "").lower()
            or any(search_query in asin.lower() for asin in p.get("asins", []))
        ]

    if marketplace_filter == "Only with marketplace sellers":
        filtered_products = [
            p for p in filtered_products if p.get("marketplace_sellers")
        ]
    elif marketplace_filter == "Only without marketplace sellers":
        filtered_products = [
            p for p in filtered_products if not p.get("marketplace_sellers")
        ]

    if seller_filter != "All Sellers":
        filtered_products = [
            p
            for p in filtered_products
            if any(
                s.get("seller_name") == seller_filter
                for s in p.get("marketplace_sellers", [])
            )
        ]

    if price_flag_filter:
        filtered_products = [
            p
            for p in filtered_products
            if any(
                s.get("price_flag") in price_flag_filter
                for s in p.get("marketplace_sellers", [])
            )
            or (p.get("badges", {}).get("worst_price_flag") in price_flag_filter)
        ]

    if sort_choice == "Product Name (A → Z)":
        filtered_products = sorted(
            filtered_products, key=lambda x: x.get("product_name") or ""
        )
    elif sort_choice == "Product Name (Z → A)":
        filtered_products = sorted(
            filtered_products, key=lambda x: x.get("product_name") or "", reverse=True
        )
    elif sort_choice == "Marketplace Sellers (High → Low)":
        filtered_products = sorted(
            filtered_products,
            key=lambda x: x.get("badges", {}).get("seller_count", 0),
            reverse=True,
        )
    elif sort_choice == "Marketplace Sellers (Low → High)":
        filtered_products = sorted(
            filtered_products, key=lambda x: x.get("badges", {}).get("seller_count", 0)
        )

    st.markdown(f"### Showing {len(filtered_products)} SKUs (after filters)")

    page_size = st.selectbox("Items per page", [10, 20, 50, 100], index=0)
    total_pages = max(1, (len(filtered_products) + page_size - 1) // page_size)

    if "explorer_page" not in st.session_state:
        st.session_state.explorer_page = 1

    if st.session_state.explorer_page > total_pages:
        st.session_state.explorer_page = total_pages

    st.markdown(f"**Page {st.session_state.explorer_page} of {total_pages}**")
    st.markdown("---")

    start = (st.session_state.explorer_page - 1) * page_size
    end = start + page_size
    page_products = filtered_products[start:end]

    for product in page_products:
        mp_count = product.get("badges", {}).get(
            "seller_count", len(product.get("marketplace_sellers", []))
        )
        worst_flag = product.get("badges", {}).get("worst_price_flag")

        seller_badge_text, seller_badge_color = seller_count_badge(mp_count)
        pf_label, pf_color = price_flag_badge(worst_flag)

        asins = ", ".join(product.get("asins", []))

        header_html = f"""
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;">
          <div style="font-weight:700;color:{PRIMARY};">{product.get('product_name')}</div>
          <div>
            <span class='badge' style='background:{seller_badge_color};'>{seller_badge_text}</span>
            <span class='badge' style='background:{pf_color};'>{pf_label}</span>
          </div>
        </div>
        """

        exp_title = f"{product.get('product_name')} (SKUs: {asins})"

        with st.expander(exp_title, expanded=False):
            st.markdown(header_html, unsafe_allow_html=True)

            st.markdown("**Product Summary**")
            smart_df(
                pd.DataFrame(
                    [
                        {
                            "Product": product.get("product_name"),
                            "SKUs": asins,
                        }
                    ]
                )
            )

            main_seller = product.get("main_seller", {})
            if main_seller:
                st.markdown("**Main Seller**")
                smart_df(
                    pd.DataFrame(
                        [
                            {
                                "Seller Name": main_seller.get("seller_name"),
                                "Ships From": main_seller.get("ships_from"),
                                "Authorized": (
                                    "Yes" if main_seller.get("authorized") else "No"
                                ),
                                "Price": fmt_money(main_seller.get("price")),
                                "Prime": "Yes" if main_seller.get("prime") else "No",
                            }
                        ]
                    )
                )

            mp_sellers = product.get("marketplace_sellers", [])
            if mp_sellers:
                st.markdown(f"**Marketplace Sellers ({len(mp_sellers)})**")
                sellers_table = []
                for s in mp_sellers:
                    sellers_table.append(
                        {
                            "Seller Name": s.get("seller_name"),
                            "Seller Price": fmt_money(s.get("seller_price")),
                            "Price Δ ($)": fmt_money(s.get("delta_abs")),
                            "Price Δ (%)": (
                                f"{s.get('delta_pct'):.2f}%"
                                if s.get("delta_pct") is not None
                                else "-"
                            ),
                            "Price Flag": s.get("price_flag"),
                        }
                    )
                smart_df(pd.DataFrame(sellers_table))
            else:
                st.info("No marketplace sellers found for this product.")

    st.markdown("---")
    col_prev, col_mid, col_next = st.columns([1, 8, 1])

    with col_prev:
        if (
            st.button("◀ Previous", key="explorer_prev")
            and st.session_state.explorer_page > 1
        ):
            st.session_state.explorer_page -= 1
            st.rerun()

    with col_next:
        if (
            st.button("Next ▶", key="explorer_next")
            and st.session_state.explorer_page < total_pages
        ):
            st.session_state.explorer_page += 1
            st.rerun()

# -----------------------------
# TAB 3: Listing Evidence
# -----------------------------

st.markdown("---")