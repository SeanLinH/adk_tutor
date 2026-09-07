"""多平台庫存的假資料與**異常偵測規則引擎**。

這個檔案裡沒有任何 LLM。這是刻意的，也是整個應用最重要的設計決定：

「這個 SKU 的可售天數是 3.2 天」「平台掛的數量比倉庫多 14 件」——這些是
**算術**，不是判斷。算術交給 Python 有三個好處：答案永遠一樣、不花錢、
出錯時有 traceback 可以看。LLM 的工作從「算給我看」變成「這 27 條異常裡，
今天最該先處理哪三條，為什麼」——那才是它比 Excel 強的地方。
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

PLATFORMS = ["官網", "蝦皮", "momo", "門市"]

# 30 個 SKU，涵蓋不同週轉速度的商品。快銷品容易斷貨、季節品容易變呆料。
# 數量刻意不少：一個多平台賣家的痛點正是「品項多到人工對不完」，只有 5 個
# SKU 的 demo 會讓人覺得「這用 Excel 看就好了」——那個質疑是對的。
_CATALOG = [
    ("SKU-1001", "備長炭竹纖維除濕包 300g x3", "居家生活", 399, 150, "快"),
    ("SKU-1002", "純棉四件式床包組（雙人）", "居家生活", 2280, 980, "中"),
    ("SKU-1003", "無線降噪耳機 Pro", "3C 周邊", 4980, 2600, "中"),
    ("SKU-1004", "USB-C 65W 氮化鎵充電器", "3C 周邊", 890, 380, "快"),
    ("SKU-1005", "不鏽鋼保溫瓶 500ml", "居家生活", 690, 260, "中"),
    ("SKU-1006", "兒童安全座椅 0-4 歲", "母嬰用品", 6800, 3900, "慢"),
    ("SKU-1007", "有機棉嬰兒包巾", "母嬰用品", 580, 210, "中"),
    ("SKU-1008", "寵物自動餵食器 4L", "寵物用品", 1580, 720, "中"),
    ("SKU-1009", "貓砂除臭活性碳包", "寵物用品", 249, 90, "快"),
    ("SKU-1010", "冬季法蘭絨睡袍", "服飾配件", 1180, 480, "慢"),
    ("SKU-1011", "防曬涼感袖套", "服飾配件", 320, 110, "慢"),
    ("SKU-1012", "藍芽體重計", "3C 周邊", 1290, 560, "中"),
    ("SKU-1013", "矽膠折疊保鮮盒 3 件組", "居家生活", 590, 220, "中"),
    ("SKU-1014", "掛燙機 手持式", "居家生活", 1490, 690, "中"),
    ("SKU-1015", "記憶棉護頸枕", "居家生活", 880, 340, "中"),
    ("SKU-1016", "磁吸行動電源 10000mAh", "3C 周邊", 1180, 520, "快"),
    ("SKU-1017", "手機支架 桌上型鋁合金", "3C 周邊", 450, 160, "中"),
    ("SKU-1018", "藍芽鍵盤 折疊式", "3C 周邊", 1680, 780, "慢"),
    ("SKU-1019", "嬰兒副食品分裝盒", "母嬰用品", 390, 140, "中"),
    ("SKU-1020", "推車遮陽罩 UPF50+", "母嬰用品", 780, 300, "慢"),
    ("SKU-1021", "學步鞋 軟底防滑", "母嬰用品", 690, 260, "中"),
    ("SKU-1022", "寵物涼感墊 M 號", "寵物用品", 520, 190, "慢"),
    ("SKU-1023", "貓抓板 瓦楞紙 2 入", "寵物用品", 360, 120, "快"),
    ("SKU-1024", "狗狗牽繩 反光加粗", "寵物用品", 480, 170, "中"),
    ("SKU-1025", "涼感短袖上衣 男", "服飾配件", 590, 210, "中"),
    ("SKU-1026", "羊毛襪 3 雙組", "服飾配件", 680, 250, "慢"),
    ("SKU-1027", "帆布托特包 大容量", "服飾配件", 890, 320, "中"),
    ("SKU-1028", "胺基酸洗面乳 120ml", "美妝保養", 420, 150, "快"),
    ("SKU-1029", "物理防曬乳 SPF50 50ml", "美妝保養", 780, 290, "中"),
    ("SKU-1030", "保濕精華液 30ml", "美妝保養", 1280, 430, "中"),
]

_VELOCITY = {"快": (18, 45), "中": (5, 18), "慢": (0, 5)}


@dataclass
class Anomaly:
    """一條異常。`impact_twd` 是拿來排序的——賣家的時間有限，先看錢。"""

    sku: str
    name: str
    kind: str
    severity: int          # 1~5，5 最嚴重
    impact_twd: int        # 預估影響金額
    detail: str
    numbers: dict = field(default_factory=dict)


# ─── 假資料 ─────────────────────────────────────────────────────────

def load_snapshot(seed: int = 42) -> list[dict]:
    """產生一份「今天的多平台庫存快照」。

    同一個 seed 一定得到同一份資料，這樣 demo 才能重現；換 seed 就換一組
    異常組合，適合演示不同狀況。
    """
    rng = random.Random(seed)
    rows: list[dict] = []
    for sku, name, category, price, cost, velocity in _CATALOG:
        lo, hi = _VELOCITY[velocity]
        sold_7d = rng.randint(lo, hi)
        # 慢銷品有一半機率整週掛零——呆滯庫存這條規則要有東西可抓，
        # 而且真實賣家的長尾商品本來就常常一週一件都沒賣。
        if velocity == "慢" and rng.random() < 0.5:
            sold_7d = 0
        on_hand = rng.randint(0, 120)
        # 平台掛的可售數：正常情況下應該等於倉庫實際庫存，但實務上常常兜不攏
        # （手動改過、平台同步失敗、門市盤點沒回報）。這裡刻意製造一些偏差。
        drift = rng.choice([0, 0, 0, rng.randint(-20, 20)])
        listed_total = max(on_hand + drift, 0)
        weights = [rng.random() for _ in PLATFORMS]
        total_w = sum(weights) or 1
        listed = {}
        remaining = listed_total
        for i, p in enumerate(PLATFORMS):
            qty = int(listed_total * weights[i] / total_w) if i < len(PLATFORMS) - 1 else remaining
            qty = max(min(qty, remaining), 0)
            listed[p] = qty
            remaining -= qty

        rows.append({
            "sku": sku,
            "name": name,
            "category": category,
            "price": price,
            "cost": cost,
            "on_hand": on_hand,                       # 倉庫實際庫存
            "listed_total": listed_total,             # 各平台掛出的可售總數
            "listed": listed,
            "pending_orders": rng.randint(0, 18),     # 已成立但還沒出貨的訂單
            "in_transit": rng.choice([0, 0, 0, rng.randint(20, 200)]),  # 在途補貨
            "sold_7d": sold_7d,
            "safety_stock": max(int(sold_7d / 7 * 10), 5),   # 安全庫存 = 10 天銷量
            "last_sold_days_ago": 0 if sold_7d else rng.choice([30, 65, 95, 140]),
        })
    return rows


# ─── 規則引擎 ───────────────────────────────────────────────────────

def days_of_cover(row: dict) -> float:
    """依近 7 日銷速，現有庫存還能撐幾天。沒有銷量時回無限大。"""
    daily = row["sold_7d"] / 7
    if daily <= 0:
        return float("inf")
    return round(row["on_hand"] / daily, 1)


def detect_anomalies(rows: list[dict]) -> list[Anomaly]:
    """跑完所有規則，回傳依影響金額排序的異常清單。

    每條規則都很無聊——就是幾個大小比較。無聊正是重點：這種判斷交給 LLM
    只會得到「有時候算錯、而且每次算法都不太一樣」的結果。
    """
    out: list[Anomaly] = []
    for r in rows:
        cover = days_of_cover(r)
        daily = r["sold_7d"] / 7

        # ① 賣超：待出貨數量已經超過倉庫庫存 → 一定會有訂單出不了
        if r["pending_orders"] > r["on_hand"]:
            short = r["pending_orders"] - r["on_hand"]
            out.append(Anomaly(
                sku=r["sku"], name=r["name"], kind="賣超", severity=5,
                impact_twd=short * r["price"],
                detail=f"待出貨 {r['pending_orders']} 件，倉庫只有 {r['on_hand']} 件，缺 {short} 件",
                numbers={"待出貨": r["pending_orders"], "庫存": r["on_hand"], "缺口": short},
            ))

        # ② 平台數量兜不攏：掛出去的可售數跟倉庫對不上
        if r["listed_total"] != r["on_hand"]:
            gap = r["listed_total"] - r["on_hand"]
            out.append(Anomaly(
                sku=r["sku"], name=r["name"], kind="平台數量不一致",
                severity=4 if gap > 0 else 2,
                impact_twd=abs(gap) * r["price"] if gap > 0 else 0,
                detail=(
                    f"平台共掛 {r['listed_total']} 件、倉庫 {r['on_hand']} 件，"
                    + ("多掛了，有再次賣超風險" if gap > 0 else "少掛了，等於自己壓住可賣的量")
                ),
                numbers={"平台合計": r["listed_total"], "倉庫": r["on_hand"], "差異": gap,
                         **r["listed"]},
            ))

        # ③ 斷貨風險：可售天數 < 7 且沒有在途補貨
        if cover < 7 and r["in_transit"] == 0 and daily > 0:
            out.append(Anomaly(
                sku=r["sku"], name=r["name"], kind="斷貨風險", severity=4,
                impact_twd=int(daily * 7 * r["price"]),
                detail=f"可售 {cover} 天（近 7 日賣 {r['sold_7d']} 件），且無在途補貨",
                numbers={"可售天數": cover, "近7日銷量": r["sold_7d"], "安全庫存": r["safety_stock"]},
            ))

        # ④ 呆滯庫存：超過 90 天沒賣掉，資金卡在架上
        if r["last_sold_days_ago"] >= 90 and r["on_hand"] > 0:
            out.append(Anomaly(
                sku=r["sku"], name=r["name"], kind="呆滯庫存", severity=3,
                impact_twd=r["on_hand"] * r["cost"],
                detail=f"已 {r['last_sold_days_ago']} 天無銷售，庫存 {r['on_hand']} 件",
                numbers={"停滯天數": r["last_sold_days_ago"], "庫存": r["on_hand"],
                         "成本壓住": r["on_hand"] * r["cost"]},
            ))

        # ⑤ 庫存過高：賣得動，但備太多（可售天數 > 120 天）
        if cover != float("inf") and cover > 120:
            out.append(Anomaly(
                sku=r["sku"], name=r["name"], kind="庫存過高", severity=2,
                impact_twd=int(r["on_hand"] * r["cost"] * 0.5),
                detail=f"可售天數 {cover} 天，週轉太慢",
                numbers={"可售天數": cover, "庫存": r["on_hand"]},
            ))

    return sorted(out, key=lambda a: (-a.severity, -a.impact_twd))


def digest(anomalies: list[Anomaly], top_n: int = 12) -> str:
    """把異常清單壓成一段給 LLM 讀的文字。

    只送前 N 條、而且已經算好數字——**不要把整個資料庫倒給模型**。
    送進去的每一個 token 都要花錢，而且雜訊越多，判讀品質越差。
    """
    if not anomalies:
        return "（今天沒有偵測到異常）"
    lines = []
    for a in anomalies[:top_n]:
        lines.append(
            f"- [{a.kind}｜嚴重度 {a.severity}｜影響約 NT$ {a.impact_twd:,}] "
            f"{a.sku} {a.name}：{a.detail}"
        )
    more = len(anomalies) - top_n
    if more > 0:
        lines.append(f"（另有 {more} 條較次要的異常未列出）")
    return "\n".join(lines)


def totals(rows: list[dict], anomalies: list[Anomaly]) -> dict:
    """UI 上方那排數字。同樣是 Python 算，不經過模型。"""
    return {
        "sku_count": len(rows),
        "anomaly_count": len(anomalies),
        "critical_count": sum(1 for a in anomalies if a.severity >= 4),
        "impact_twd": sum(a.impact_twd for a in anomalies),
        "stock_value": sum(r["on_hand"] * r["cost"] for r in rows),
    }


# ─── 給 agent 用的工具 ──────────────────────────────────────────────
# 只有「需要 agent 自己決定要不要查」的東西才做成工具。日報用得到的數字
# 已經在 digest() 裡了，不必讓模型再查一次。

_SNAPSHOT_CACHE: dict[str, list[dict]] = {}


def _current_rows() -> list[dict]:
    return _SNAPSHOT_CACHE.get("current", [])


def set_current_snapshot(rows: list[dict]) -> None:
    """讓工具函式能讀到這一輪的快照。工具的參數只該放模型決定得了的東西
    （SKU 編號），資料本身從這裡拿。"""
    _SNAPSHOT_CACHE["current"] = rows


def get_sku_detail(sku: str) -> dict:
    """Get the full inventory detail of one SKU, including per-platform listings."""
    for r in _current_rows():
        if r["sku"].upper() == sku.strip().upper():
            cover = days_of_cover(r)
            # 沒有銷量時 days_of_cover() 是 float("inf")，**絕對不能直接回傳**：
            # 工具的回傳值會被序列化成 JSON 放進對話歷史再送回模型，而
            # `Infinity` 不是合法的 JSON，整個請求會被 API 用 400 打回
            # （錯誤訊息是 `Invalid JSON payload received. Unexpected token`，
            # 而且指的是對話歷史，不是你這次的輸入，很難一眼看出來源）。
            # 通則：工具只能回傳 JSON 安全的值——不要有 inf、NaN、datetime、
            # set、自訂 class。
            return {
                "found": True,
                **r,
                "days_of_cover": None if cover == float("inf") else cover,
                "note": "近 7 日無銷售，可售天數無法估算" if cover == float("inf") else "",
            }
    return {"found": False, "sku": sku}


def draft_restock_order(sku: str, quantity: int) -> dict:
    """Draft a restock purchase order for a SKU. Does not submit it."""
    for r in _current_rows():
        if r["sku"].upper() == sku.strip().upper():
            return {
                "drafted": True,
                "sku": r["sku"],
                "name": r["name"],
                "quantity": quantity,
                "estimated_cost_twd": quantity * r["cost"],
                "status": "草稿，尚未送出——需採購人員確認供應商與交期",
            }
    return {"drafted": False, "sku": sku, "reason": "查無此 SKU"}
