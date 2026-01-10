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

    @st.dialog("Average Impact Stats", width="large")
    def dlg_avg_stats(avg_pct_all, avg_abs_all, avg_pct_gouged_only):
        st.markdown("### Average Overprice Statistics")
        st.write("**Avg % Overprice (All):**", f"{avg_pct_all:.2f}%")
        st.write("**Avg $ Overprice (All):**", fmt_money(avg_abs_all, 2))
        st.write("**Avg % Overprice (Gouged Only):**", f"{avg_pct_gouged_only:.2f}%")

    @st.dialog("SKU Details", width="large")
    def dlg_asin_details(seller_name, asin_details):
        st.markdown(f"### 🔍 {seller_name}")
        st.write(f"**Total SKUs:** {len(asin_details)}")
        st.markdown("---")

        details_df = pd.DataFrame(
            [
                {
                    "SKU": d["asin"],
                    "Title": d["title"],
                    "Base Price": fmt_money(d["base_price"], 2),
                    "Seller Price": fmt_money(d["seller_price"], 2),
                    "Δ ($)": fmt_money(d["delta_abs"], 2),
                    "Δ (%)": f"{d['delta_pct']:.2f}%",
                }
                for d in asin_details
            ]
        )
        smart_df(details_df, max_height=600)


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
tab_insights, tab_explorer = st.tabs(
    [" Marketplace Insights", " Product Listing Explorer"]
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
    st.markdown("###  Top 10 Most Gouged SKUs with Seller Breakdown")

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
# TAB 2: Product Listing Explorer
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
