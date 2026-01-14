import json
import re
from pathlib import Path
from collections import defaultdict


INPUT_FILE = "unique_trufru.json"
OUTPUT_FILE = "validated_json/trufru_baseprice_payload.json"


PCT_THRESHOLD = 20.0
ABS_THRESHOLD = 2.0


_money_re = re.compile(r"\$([0-9]+(?:\.[0-9]+)?)")


# --------------------------------------------------
# Helpers
# --------------------------------------------------
def parse_money_max(text):
    if not text:
        return None
    s = str(text).replace(",", "")
    vals = _money_re.findall(s)
    return float(max(vals, key=lambda v: float(v))) if vals else None


def norm_seller(name):
    return (str(name or "")).strip()


def norm_key(name):
    return norm_seller(name).lower()
def find_undercut_sellers(raw_products):
    """
    Find marketplace sellers selling below the base (main) seller price.
    Returns a list of detailed undercut listings.
    """

    undercut_listings = []

    for p in raw_products:
        asin = p.get("asin")
        title = p.get("title")
        base_seller = norm_seller(p.get("sold_by"))
        base_price = parse_money_max(p.get("price"))

        if not base_price:
            continue

        other_sellers = p.get("other_sellers") or []
        if not other_sellers:
            continue

        for s in other_sellers:
            seller_name = norm_seller(s.get("sold_by"))
            seller_price = parse_money_max(s.get("price"))

            if seller_price is None:
                continue

            # 👇 CORE CONDITION: Seller price lower than base price
            if seller_price < base_price:
                delta_abs = round(seller_price - base_price, 2)
                delta_pct = round((delta_abs / base_price) * 100, 4)

                undercut_listings.append({
                    "asin": asin,
                    "title": title,
                    "base_seller": base_seller,
                    "base_price": round(base_price, 2),
                    "seller_name": seller_name,
                    "seller_price": round(seller_price, 2),
                    "delta_abs": delta_abs,          # negative value
                    "delta_pct": delta_pct,          # negative %
                    "ships_from": s.get("ships_from"),
                    "authorized": s.get("is_authorized"),
                    "prime": s.get("prime"),
                    "rating_stars": s.get("rating_stars"),
                    "rating_count": s.get("rating_count"),
                    "positive_rating_percent": s.get("positive_rating_percent"),
                })

    return undercut_listings
def find_repeated_sellers(comparisons, min_products=2):
    """
    Find sellers appearing across multiple products (ASINs).
    Returns seller → list of products with pricing details.
    """
    seller_map = defaultdict(lambda: {
        "seller_name": None,
        "products": {}
    })

    for row in comparisons:
        seller = row.get("seller_name")
        asin = row.get("asin")

        if not seller or not asin:
            continue

        seller_entry = seller_map[seller]
        seller_entry["seller_name"] = seller

        if asin not in seller_entry["products"]:
            seller_entry["products"][asin] = {
                "asin": asin,
                "title": row.get("title"),
                "base_seller": row.get("base_seller"),
                "base_price": row.get("base_price"),
                "listings": []
            }

        seller_entry["products"][asin]["listings"].append({
            "seller_price": row.get("seller_price"),
            "delta_abs": row.get("delta_abs"),
            "delta_pct": row.get("delta_pct"),
            "gouged": row.get("gouged")
        })

    repeated_sellers = []
    for seller, data in seller_map.items():
        products = list(data["products"].values())
        if len(products) >= min_products:
            repeated_sellers.append({
                "seller_name": seller,
                "product_count": len(products),
                "products": products
            })

    repeated_sellers.sort(
        key=lambda x: x["product_count"],
        reverse=True
    )

    return repeated_sellers



# --------------------------------------------------
# Load data
# --------------------------------------------------
data = json.loads(Path(INPUT_FILE).read_text(encoding="utf-8"))

products_total = len(data)

comparisons = []
products_with_other_sellers_list = []
unique_marketplace_sellers = set()

sku_gouge_map = defaultdict(list)
seller_sku_map = defaultdict(set)
seller_price_map = defaultdict(list)

# NEW: Track ASINs per seller with details
seller_asin_details = defaultdict(list)


# --------------------------------------------------
# Main normalization loop
# --------------------------------------------------
for p in data:
    asin = p.get("asin")
    title = p.get("title")
    base_seller = norm_seller(p.get("sold_by"))
    base_price = parse_money_max(p.get("price"))

    other = p.get("other_sellers") or []
    if not other:
        continue

    products_with_other_sellers_list.append({
        "asin": asin,
        "title": title
    })

    if not base_price:
        continue

    for osel in other:
        seller_name = norm_seller(osel.get("sold_by"))
        seller_price = parse_money_max(osel.get("price"))

        if not seller_price:
            continue

        unique_marketplace_sellers.add(seller_name)

        delta_abs = seller_price - base_price
        delta_pct = (delta_abs / base_price) * 100
        gouged = (delta_pct >= PCT_THRESHOLD) and (delta_abs >= ABS_THRESHOLD)

        row = {
            "asin": asin,
            "title": title,
            "base_price": round(base_price, 2),
            "base_seller": base_seller,
            "seller_name": seller_name,
            "seller_price": round(seller_price, 2),
            "delta_abs": round(delta_abs, 2),
            "delta_pct": round(delta_pct, 4),
            "gouged": gouged
        }

        comparisons.append(row)

        if gouged:
            sku_gouge_map[asin].append(row)
            seller_sku_map[seller_name].add(asin)
            seller_price_map[seller_name].append(delta_pct)
            
            # NEW: Track ASIN details for this seller
            seller_asin_details[seller_name].append({
                "asin": asin,
                "title": title,
                "base_price": round(base_price, 2),
                "seller_price": round(seller_price, 2),
                "delta_abs": round(delta_abs, 2),
                "delta_pct": round(delta_pct, 4)
            })


# --------------------------------------------------
# Metrics
# --------------------------------------------------
listing_comparisons_count = len(comparisons)
gouged_rows = [c for c in comparisons if c["gouged"]]

avg_overprice_pct_all = (
    sum(c["delta_pct"] for c in comparisons) / listing_comparisons_count
    if listing_comparisons_count else 0.0
)

avg_overprice_abs_all = (
    sum(c["delta_abs"] for c in comparisons) / listing_comparisons_count
    if listing_comparisons_count else 0.0
)

avg_overprice_pct_gouged_only = (
    sum(c["delta_pct"] for c in gouged_rows) / len(gouged_rows)
    if gouged_rows else 0.0
)


# --------------------------------------------------
# Top 10 Most Gouged SKUs (WITH FULL DETAILS)
# --------------------------------------------------
top_10_most_gouged_skus = []

for asin, rows in sku_gouge_map.items():
    max_pct = max(r["delta_pct"] for r in rows)
    max_abs = max(r["delta_abs"] for r in rows)
    
    gouging_sellers = [
        {
            "seller_name": r["seller_name"],
            "seller_price": r["seller_price"],
            "delta_abs": r["delta_abs"],
            "delta_pct": r["delta_pct"]
        }
        for r in rows
    ]
    
    gouging_sellers = sorted(
        gouging_sellers,
        key=lambda x: (x["delta_pct"], x["delta_abs"]),
        reverse=True
    )
    
    top_10_most_gouged_skus.append({
        "asin": asin,
        "title": rows[0]["title"],
        "base_seller": rows[0]["base_seller"],
        "base_price": rows[0]["base_price"],
        "max_overprice_pct": max_pct,
        "max_overprice_abs": max_abs,
        "gouged_listings": len(rows),
        "gouging_sellers": gouging_sellers
    })

top_10_most_gouged_skus = sorted(
    top_10_most_gouged_skus,
    key=lambda x: (x["max_overprice_pct"], x["max_overprice_abs"]),
    reverse=True
)[:10]


# --------------------------------------------------
# Seller tables (WITH ASIN DETAILS)
# --------------------------------------------------

# High Price Seller Analysis
high_price_seller_analysis = []
for seller, vals in seller_price_map.items():
    asins = list(seller_sku_map[seller])
    asin_details = seller_asin_details[seller]
    
    high_price_seller_analysis.append({
        "seller_name": seller,
        "total_skus": len(asins),
        "overpriced_skus": len(asins),
        "avg_delta_percent": round(sum(vals) / len(vals), 2),
        "asins": ", ".join(asins),
        "asin_details": asin_details
    })

high_price_seller_analysis = sorted(
    high_price_seller_analysis,
    key=lambda x: x["avg_delta_percent"],
    reverse=True
)


# Seller SKU Impact
seller_sku_impact = []
for seller, skus in seller_sku_map.items():
    asins = list(skus)
    asin_details = seller_asin_details[seller]
    
    seller_sku_impact.append({
        "seller_name": seller,
        "sku_count": len(asins),
        "asins": ", ".join(asins),
        "asin_details": asin_details
    })

seller_sku_impact = sorted(
    seller_sku_impact,
    key=lambda x: x["sku_count"],
    reverse=True
)


# Seller Gouging Summary (for Top Violators)
seller_gouging_summary = []
for seller, vals in seller_price_map.items():
    asins = list(seller_sku_map[seller])
    asin_details = seller_asin_details[seller]
    
    seller_gouging_summary.append({
        "seller_name": seller,
        "gouged_listings": len(vals),
        "avg_overprice_pct": round(sum(vals) / len(vals), 2),
        "asins": ", ".join(asins),
        "asin_details": asin_details
    })

seller_gouging_summary = sorted(
    seller_gouging_summary,
    key=lambda x: (x["gouged_listings"], x["avg_overprice_pct"]),
    reverse=True
)

top_violators = seller_gouging_summary[:10]


# --------------------------------------------------
# Product Listings Builder
# --------------------------------------------------
def build_product_listings(raw_products):
    product_listings = []

    for p in raw_products:
        asin = p.get("asin")
        product_name = p.get("product_name") or p.get("title")
        category = p.get("category")

        main = p.get("main_seller") or {}
        others = p.get("other_sellers") or []

        pack_options = [{
            "asin": asin,
            "title": p.get("title"),
            "price": parse_money_max(p.get("price")),
            "unit_price": p.get("unit_price"),
            "prime": p.get("prime"),
            "flavor": p.get("flavor"),
            "amazon_url": p.get("final_url")
        }]

        main_price = parse_money_max(main.get("price")) or parse_money_max(p.get("price"))
        
        main_seller = {
            "seller_name": norm_seller(
                main.get("seller_name") or p.get("sold_by")
            ),
            "ships_from": norm_seller(
                main.get("ships_from") or p.get("ships_from")
            ),
            "authorized": main.get("is_authorized"),
            "price": main_price,
            "unit_price": main.get("unit_price") or p.get("unit_price"),
            "prime": main.get("prime", p.get("prime"))
        }


        mp_sellers = []
        worst_flag = "Fair Price"

        for s in others:
            seller_price = parse_money_max(s.get("price"))
            amazon_unit_price = main_seller.get("unit_price")
            seller_unit_price = s.get("unit_price")

            unit_price_delta = (
                round(float(seller_unit_price) - float(amazon_unit_price), 2)
                if seller_unit_price and amazon_unit_price else None
            )

            delta_abs = None
            if seller_price is not None and main_price is not None:
                delta_abs = round(float(seller_price) - float(main_price), 2)

            delta_pct = None
            if delta_abs is not None and main_price and float(main_price) > 0:
                delta_pct = round((delta_abs / float(main_price)) * 100, 4)

            is_gouged = (
                delta_pct is not None and
                delta_abs is not None and
                delta_pct >= PCT_THRESHOLD and
                delta_abs >= ABS_THRESHOLD
            )

            price_flag = "Price Gouging" if is_gouged else "Fair Price"
            if price_flag == "Price Gouging":
                worst_flag = "Price Gouging"

            mp_sellers.append({
                "seller_name": s.get("sold_by"),
                "ships_from": s.get("ships_from"),
                "authorized": s.get("is_authorized"),
                "seller_price": seller_price,
                "seller_unit_price": seller_unit_price,
                "amazon_unit_price": amazon_unit_price,
                "unit_price_delta": unit_price_delta,
                "delta_abs": delta_abs,
                "delta_pct": delta_pct,
                "price_flag": price_flag,
                "rating_stars": s.get("rating_stars"),
                "rating_count": s.get("rating_count"),
                "positive_rating_percent": s.get("positive_rating_percent"),
            })

        product_listings.append({
            "product_name": product_name,
            "category": category,
            "asins": [asin],
            "pack_count": 1,
            "badges": {
                "seller_count": len(mp_sellers),
                "worst_price_flag": worst_flag
            },
            "summary": {
                "representative_asin": asin,
                "amazon_url": p.get("final_url")
            },
            "pack_options": pack_options,
            "main_seller": main_seller,
            "marketplace_sellers": mp_sellers
        })

    return product_listings


# --------------------------------------------------
# Final payload
# --------------------------------------------------
undercut_sellers = find_undercut_sellers(data)
repeated_sellers = find_repeated_sellers(comparisons)
payload = {
    "thresholds": {
        "pct_threshold": PCT_THRESHOLD,
        "abs_threshold": ABS_THRESHOLD,
        "currency": "USD"
    },
    "metrics": {
        "products_total": products_total,
        "products_with_other_sellers": len(products_with_other_sellers_list),
        "listing_comparisons_count": listing_comparisons_count,
        "gouged_listings_count": len(gouged_rows),
        "avg_overprice_pct_all": round(avg_overprice_pct_all, 4),
        "avg_overprice_abs_all": round(avg_overprice_abs_all, 4),
        "avg_overprice_pct_gouged_only": round(avg_overprice_pct_gouged_only, 4)
    },
    "undercut_sellers_count": len(undercut_sellers),
    "undercut_sellers": undercut_sellers,
    "repeated_sellers_count": len(repeated_sellers),
    "repeated_sellers": repeated_sellers,

    "comparisons": comparisons,
    "products_with_other_sellers_list": products_with_other_sellers_list,
    "unique_marketplace_sellers": sorted(unique_marketplace_sellers),
    "top_10_most_gouged_skus": top_10_most_gouged_skus,
    "seller_gouging_summary": seller_gouging_summary,
    "seller_sku_impact": seller_sku_impact,
    "high_price_seller_analysis": high_price_seller_analysis,
    "top_violators": top_violators,

}

payload["product_listings"] = build_product_listings(data)

Path(OUTPUT_FILE).write_text(json.dumps(payload, indent=2), encoding="utf-8")
print("✔ Wrote:", OUTPUT_FILE)
