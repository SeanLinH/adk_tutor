"""客服工單應用的假資料與工具。

這裡有兩種函式，分得很清楚，理由見 README 的「什麼給 LLM、什麼留給 Python」：

* **給 agent 當工具用的**（`lookup_order` / `check_shipping_status` /
  `check_return_policy`）——查得到就回事實，查不到就明講。它們有英文
  docstring，因為那份 docstring 會變成送給模型的工具說明。
* **只給 Python 用的**（`needs_human_review`）——人工審核的判斷條件不該由
  LLM 決定，所以它不是工具，是一段普通的 if。
"""

from __future__ import annotations

from datetime import date, timedelta

# ─── 假訂單資料庫 ────────────────────────────────────────────────────
# 刻意涵蓋幾種現實情況：已送達很久的、還在運送中的、金額很大的、查無此單的。

_TODAY = date.today()


def _days_ago(n: int) -> str:
    return (_TODAY - timedelta(days=n)).isoformat()


ORDERS: dict[str, dict] = {
    "SP-20250412": {
        "order_id": "SP-20250412",
        "platform": "蝦皮",
        "customer": "林小姐",
        "item": "備長炭竹纖維除濕包 300g x3 入",
        "category": "居家生活",
        "amount_twd": 399,
        "ordered_at": _days_ago(12),
        "delivered_at": _days_ago(5),
        "status": "已送達",
        "vip": False,
    },
    "MO-20250408": {
        "order_id": "MO-20250408",
        "platform": "momo",
        "customer": "陳先生",
        "item": "無線降噪耳機 Pro",
        "category": "3C 周邊",
        "amount_twd": 4980,
        "ordered_at": _days_ago(20),
        "delivered_at": _days_ago(16),
        "status": "已送達",
        "vip": True,
    },
    "WB-20250420": {
        "order_id": "WB-20250420",
        "platform": "官網",
        "customer": "黃太太",
        "item": "純棉四件式床包組（雙人）",
        "category": "居家生活",
        "amount_twd": 2280,
        "ordered_at": _days_ago(4),
        "delivered_at": "",
        "status": "運送中",
        "vip": False,
    },
    "SP-20250401": {
        "order_id": "SP-20250401",
        "platform": "蝦皮",
        "customer": "吳小姐",
        "item": "兒童安全座椅 0-4 歲",
        "category": "母嬰用品",
        "amount_twd": 6800,
        "ordered_at": _days_ago(30),
        "delivered_at": _days_ago(26),
        "status": "已送達",
        "vip": False,
    },
}

# 各類別的退貨規則。台灣的七天鑑賞期是法定下限，但不同品類實務上會加條件。
_RETURN_RULES: dict[str, dict] = {
    "居家生活": {"window_days": 7, "restocking_fee_pct": 0, "note": "需附完整包裝"},
    "3C 周邊": {"window_days": 7, "restocking_fee_pct": 0, "note": "需附完整配件與保固卡"},
    "母嬰用品": {"window_days": 7, "restocking_fee_pct": 0, "note": "拆封後僅接受瑕疵退貨"},
    "食品飲料": {"window_days": 0, "restocking_fee_pct": 0, "note": "食品類不適用鑑賞期"},
}
_DEFAULT_RULE = {"window_days": 7, "restocking_fee_pct": 0, "note": "一般規則"}


# ─── Agent 工具 ─────────────────────────────────────────────────────

def lookup_order(order_id: str) -> dict:
    """Look up an order by its ID. Returns order details or found=False."""
    order = ORDERS.get(order_id.strip().upper())
    if not order:
        return {
            "found": False,
            "order_id": order_id,
            "hint": "查無此訂單編號，請向客戶確認編號是否正確。",
        }
    return {"found": True, **order}


def check_shipping_status(order_id: str) -> dict:
    """Check the shipping timeline of an order."""
    order = ORDERS.get(order_id.strip().upper())
    if not order:
        return {"found": False, "order_id": order_id}
    if order["status"] == "運送中":
        days = (_TODAY - date.fromisoformat(order["ordered_at"])).days
        return {
            "found": True,
            "status": "運送中",
            "days_since_order": days,
            "delayed": days > 5,
            "carrier": "黑貓宅急便",
            "note": "超過 5 天仍未送達視為異常，可代客戶向物流查件。",
        }
    return {
        "found": True,
        "status": order["status"],
        "delivered_at": order["delivered_at"],
        "carrier": "黑貓宅急便",
    }


def check_return_policy(order_id: str) -> dict:
    """Check whether a return is still allowed for an order under the return policy."""
    order = ORDERS.get(order_id.strip().upper())
    if not order:
        return {"found": False, "order_id": order_id}

    # 天數由這裡算，**不是**讓模型算好再當參數傳進來。
    # 實測過：把 days_since_delivery 開成工具參數時，模型會憑印象填一個數字
    # （送達 16 天的訂單填成 1），整個政策判斷就跟著錯。日期相減是算術，
    # 算術留在 Python——同樣的原則見 demo/inventory_watch/README.md。
    days = days_since_delivery(order)
    rule = _RETURN_RULES.get(order["category"], _DEFAULT_RULE)
    within = 0 <= days <= rule["window_days"]

    if days < 0:      # 還在運送中，鑑賞期根本還沒開始起算
        note = "商品尚未送達，七天鑑賞期自送達日起算，目前無法辦理退貨。"
    elif within:
        note = ""
    else:
        note = "已超過鑑賞期，但商品瑕疵不受鑑賞期限制，仍可依消保法處理。"

    return {
        "found": True,
        "order_id": order["order_id"],
        "category": order["category"],
        "delivered": days >= 0,
        "days_since_delivery": days if days >= 0 else "尚未送達",
        "window_days": rule["window_days"],
        "eligible": within,
        "restocking_fee_pct": rule["restocking_fee_pct"],
        "note": rule["note"],
        "exception": note,
    }


def days_since_delivery(order: dict) -> int:
    """算出送達至今幾天；還沒送達回 -1。給 UI 顯示用，不是 agent 工具。"""
    if not order.get("delivered_at"):
        return -1
    return (_TODAY - date.fromisoformat(order["delivered_at"])).days


# ─── 人工審核閘門（純 Python，不給 LLM 決定）──────────────────────────

# 這些門檻是「公司政策」，不是「判斷題」。寫成常數才能被稽核、被改，
# 而且不會因為換一個模型或改一句 prompt 就悄悄變動。
AUTO_APPROVE_MAX_TWD = 1000
HIGH_RISK_CATEGORIES = ("商品瑕疵", "客服態度")


def needs_human_review(triage: dict, order: dict | None) -> tuple[bool, list[str]]:
    """判斷這張工單能不能自動回覆，回傳 (是否需人工, 理由清單)。

    刻意**不做成 agent 工具**：要不要讓真人看過，是公司要承擔的責任，
    不該由模型在 prompt 裡自由心證。LLM 負責讀懂客訴、查政策、擬草稿；
    「能不能就這樣寄出去」由這段 if 決定。
    """
    reasons: list[str] = []

    if triage.get("urgency") == "高":
        reasons.append("客訴急迫度為「高」")
    if triage.get("category") in HIGH_RISK_CATEGORIES:
        reasons.append(f"類型「{triage.get('category')}」屬高風險，需真人確認")
    if triage.get("mentions_authority"):
        reasons.append("客戶提到消保官／申訴／法律途徑")
    if order:
        if order["amount_twd"] > AUTO_APPROVE_MAX_TWD:
            reasons.append(
                f"訂單金額 NT$ {order['amount_twd']} 超過自動處理上限 "
                f"NT$ {AUTO_APPROVE_MAX_TWD}"
            )
        if order.get("vip"):
            reasons.append("VIP 客戶")
    else:
        reasons.append("查無對應訂單，無法核對事實")

    return bool(reasons), reasons
