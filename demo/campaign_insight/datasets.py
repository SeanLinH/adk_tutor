"""雙 11 檔期的假資料：廣告、銷售、庫存三個資料源。

這三份資料刻意被設計成「單看任何一份都會下錯結論」：

* 只看**廣告**：ROAS 4.0，花 18 萬帶回 72 萬營收 → 看起來很成功，該加碼。
* 只看**銷售**：營收確實成長，但平均折扣 32%、毛利率只剩 18%
  → 毛利 12.96 萬 < 廣告費 18 萬，這檔其實是賠的。
* 只看**庫存**：賣最好的充電器只剩 3.2 天可售，而廣告還在推它
  → 接下來每天的廣告費會把人送到一個快缺貨的頁面。

要得到「該立刻停掉充電器的廣告、把預算移到毛利高的耳機」這個結論，必須把
三份資料**交叉**看。這正是這個 demo 想演示的協作情境。
"""

from __future__ import annotations

CAMPAIGN = "2025 雙11檔期"

# ─── 廣告資料 ───────────────────────────────────────────────────────

_ADS = {
    "Meta（FB/IG）": {
        "spend_twd": 98_000, "impressions": 1_420_000, "clicks": 21_300,
        "conversions": 612, "attributed_revenue_twd": 396_000,
        "top_creative": "充電器 65W 限時 5 折",
    },
    "Google Ads": {
        "spend_twd": 62_000, "impressions": 880_000, "clicks": 12_100,
        "conversions": 388, "attributed_revenue_twd": 251_000,
        "top_creative": "氮化鎵充電器 比價關鍵字",
    },
    "LINE LAP": {
        "spend_twd": 20_000, "impressions": 310_000, "clicks": 3_900,
        "conversions": 96, "attributed_revenue_twd": 73_000,
        "top_creative": "全站滿千折百",
    },
}

# ─── 銷售資料 ───────────────────────────────────────────────────────

_SALES = {
    "period": CAMPAIGN,
    "revenue_twd": 720_000,
    "orders": 1_096,
    "avg_order_value_twd": 657,
    "avg_discount_pct": 32,
    "gross_margin_pct": 18,          # 折扣吃掉毛利之後的實際毛利率
    "new_customer_pct": 71,
    "repeat_rate_pct": 9,            # 檔期客的回購率，明顯低於平時
    "baseline_repeat_rate_pct": 24,  # 平時（非檔期）的回購率
    "top_skus": [
        {"sku": "SKU-1004", "name": "USB-C 65W 氮化鎵充電器",
         "revenue_twd": 295_000, "units": 662, "margin_pct": 11},
        {"sku": "SKU-1003", "name": "無線降噪耳機 Pro",
         "revenue_twd": 184_000, "units": 46, "margin_pct": 34},
        {"sku": "SKU-1001", "name": "備長炭竹纖維除濕包 300g x3",
         "revenue_twd": 88_000, "units": 285, "margin_pct": 41},
        {"sku": "SKU-1009", "name": "貓砂除臭活性碳包",
         "revenue_twd": 53_000, "units": 240, "margin_pct": 38},
    ],
}

# ─── 庫存資料 ───────────────────────────────────────────────────────

_STOCK = {
    "SKU-1004": {"name": "USB-C 65W 氮化鎵充電器", "on_hand": 118,
                 "daily_sales": 37, "days_of_cover": 3.2, "in_transit": 0,
                 "restock_lead_days": 21},
    "SKU-1003": {"name": "無線降噪耳機 Pro", "on_hand": 240,
                 "daily_sales": 3, "days_of_cover": 80.0, "in_transit": 60,
                 "restock_lead_days": 14},
    "SKU-1001": {"name": "備長炭竹纖維除濕包 300g x3", "on_hand": 610,
                 "daily_sales": 16, "days_of_cover": 38.1, "in_transit": 0,
                 "restock_lead_days": 7},
    "SKU-1009": {"name": "貓砂除臭活性碳包", "on_hand": 92,
                 "daily_sales": 13, "days_of_cover": 7.1, "in_transit": 300,
                 "restock_lead_days": 5},
}


# ─── 三個工具，各自只看得到自己的資料源 ─────────────────────────────
# 這是刻意的：每個分析師 agent 只配一把鑰匙，它就不可能「順便」談論別人的
# 領域。要跨領域的結論，只能由上層把三份回答湊起來——這讓「誰說了什麼」
# 在畫面上是可追溯的。

def get_ad_metrics(channel: str = "") -> dict:
    """Get ad performance for the campaign. Pass empty channel for all channels."""
    if channel and channel in _ADS:
        data = {channel: _ADS[channel]}
    else:
        data = _ADS
    out = {}
    for name, d in data.items():
        ctr = round(d["clicks"] / d["impressions"] * 100, 2)
        cpc = round(d["spend_twd"] / d["clicks"], 1)
        cpa = round(d["spend_twd"] / d["conversions"], 1)
        roas = round(d["attributed_revenue_twd"] / d["spend_twd"], 2)
        out[name] = {**d, "ctr_pct": ctr, "cpc_twd": cpc, "cpa_twd": cpa, "roas": roas}
    total_spend = sum(d["spend_twd"] for d in data.values())
    total_rev = sum(d["attributed_revenue_twd"] for d in data.values())
    return {
        "campaign": CAMPAIGN,
        "channels": out,
        "total_spend_twd": total_spend,
        "total_attributed_revenue_twd": total_rev,
        "blended_roas": round(total_rev / total_spend, 2),
    }


def get_sales_metrics(period: str = "") -> dict:
    """Get sales performance for the campaign: revenue, margin, top SKUs."""
    return dict(_SALES)


def get_stock_levels(sku: str = "") -> dict:
    """Get current stock and days of cover. Pass empty sku for all key SKUs."""
    if sku:
        key = sku.strip().upper()
        if key in _STOCK:
            return {"found": True, key: _STOCK[key]}
        return {"found": False, "sku": sku}
    return {"found": True, **_STOCK}


# ─── 給 UI 直接顯示的原始資料 ───────────────────────────────────────

def raw_tables() -> dict[str, list[dict]]:
    """三份資料攤平成表格，讓使用者可以自己核對 agent 有沒有講錯。"""
    ads = get_ad_metrics()
    return {
        "廣告": [
            {"渠道": k, "花費": v["spend_twd"], "點擊": v["clicks"],
             "CTR%": v["ctr_pct"], "CPC": v["cpc_twd"], "轉換": v["conversions"],
             "CPA": v["cpa_twd"], "歸因營收": v["attributed_revenue_twd"],
             "ROAS": v["roas"], "主力素材": v["top_creative"]}
            for k, v in ads["channels"].items()
        ],
        "銷售": [
            {"SKU": s["sku"], "商品": s["name"], "營收": s["revenue_twd"],
             "件數": s["units"], "毛利率%": s["margin_pct"]}
            for s in _SALES["top_skus"]
        ],
        "庫存": [
            {"SKU": k, "商品": v["name"], "庫存": v["on_hand"],
             "日均銷量": v["daily_sales"], "可售天數": v["days_of_cover"],
             "在途": v["in_transit"], "補貨前置天數": v["restock_lead_days"]}
            for k, v in _STOCK.items()
        ],
    }
