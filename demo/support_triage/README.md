# 🎧 客訴工單分流 + 退換貨

> 客訴進來 → 分類成**結構化工單** → 查訂單/物流/退貨政策 → 擬回覆草稿 →
> **由 Python 決定這封能不能自動寄出**。

```bash
uv run streamlit run demo/support_triage/app.py
```

## 這在解什麼問題

客服的工作量分兩種：**判斷**（這是哪種問題、政策允許怎麼處理）和**打字**
（把判斷寫成一封得體的信）。中小型電商的客服通常一人身兼數職，時間都花在
第二種，第一種反而做得急就章——同樣的瑕疵客訴，早上那封賠運費、下午那封
不賠，客戶截圖一比就變成第二次客訴。

這個 demo 把兩件事分開：**判斷交給流程與規則**（可稽核、可修改），
**打字交給模型**。而且刻意保留一道人工閘門——高風險的信，模型寫完也不會寄。

## ADK 設計邏輯

### 架構

```
客戶訊息（自由文字）
      ↓
 triage_agent      output_schema=Triage → 產出一份 JSON 工單
      ↓  state["triage"] = {"category": "商品瑕疵", "urgency": "高", ...}
 policy_agent      FunctionTool：lookup_order / check_shipping_status
      ↓                          / check_return_policy
      ↓  state["policy_result"]
 reply_agent       依查證結論擬信
      ↓  state["reply_draft"]
━━━━━━━━ agent 到此為止 ━━━━━━━━
needs_human_review(triage, order)   ← 純 Python 的 if
      ↓
  可自動寄出 / 需真人核准 → UI 上的 ✅ 核准、↩️ 退回 + 稽核紀錄
```

### 用到的 ADK 元件

| 元件 | 在這裡的角色 |
|---|---|
| `SequentialAgent` | 分類 → 查證 → 擬稿的固定順序 |
| `output_schema`（Pydantic） | 讓分類結果變成**程式讀得懂的 dict**，不是一段話 |
| `FunctionTool` | 查訂單、查物流、查退貨政策 |
| `output_key` + session state | 每一站的產物存進 state，最後由 UI 一次撈出來 |
| `RunConfig(streaming_mode=SSE)` | 逐字串流——分類階段看得到 JSON 一個欄位一個欄位長出來 |

### 為什麼分類要用 `output_schema`

因為分類結果**下游是程式在用**：`needs_human_review()` 要讀 `urgency`、
UI 的 metric 要讀 `category` 跟 `order_id`。如果讓 agent 用自然語言回
「我覺得這件事蠻緊急的」，程式就得反過來用字串比對去猜它的意思——那是整條
流程裡最容易壞、又最難測的一段。

設了 `output_schema` 之後，ADK 會做兩件事：要求模型輸出 JSON，並把它驗證成
dict 存進 `state["triage"]`。UI 直接讀 dict 就好。

代價是 **`output_schema` 的 agent 不能有工具、也不能 transfer**（ADK 的限制，
因為它必須把整個回應變成一份 JSON）。這聽起來像限制，實際上逼出了乾淨的分工：
分類就只做分類，要查資料是下一站的事。

### 為什麼閘門是 Python 的 if，不是第四個 agent

`tools.py` 裡的 `needs_human_review()` 刻意**不是** `FunctionTool`：

```python
AUTO_APPROVE_MAX_TWD = 1000
HIGH_RISK_CATEGORIES = ("商品瑕疵", "客服態度")
```

這幾行是**公司政策**，不是判斷題。寫成常數才能被稽核、被老闆改、被 code
review；寫進 prompt 就會變成「換一個模型、或某天模型心情不同」就悄悄改變的東西。

### 工具參數也適用同一條線（實際踩過）

`check_return_policy` 一開始的簽名是
`check_return_policy(product_category, days_since_delivery)`，讓 agent 自己
把「送達日期」換算成天數再傳進來。實際跑一次就露餡了——工具軌跡上出現：

```
policy_agent → check_return_policy(days_since_delivery=1, product_category='3C 周邊')
```

那張訂單是 **16 天前**送達的。模型沒有真的算，它憑印象填了一個數字，
於是政策判斷整個歪掉。改成 `check_return_policy(order_id)`、天數在函式內部
用 `date` 相減之後，這個錯誤就不可能再發生了。

原則：**工具參數只放模型「決定得了」的東西**（要查哪張訂單），
不要放它「算得出來」的東西（那張訂單送達幾天了）。

一個實用的分界線：

| 這件事的性質 | 交給誰 |
|---|---|
| 讀懂客戶在氣什麼 | LLM |
| 從自由文字抓出訂單編號 | LLM |
| 訂單金額有沒有超過 1000 | Python |
| 這封信能不能不經人眼就寄出 | Python（而且要留紀錄） |
| 把結論寫成一封得體的信 | LLM |

### 人工審核（HITL）的兩種做法

這個 demo 把閘門放在**流程之外**：agent 跑完，UI 拿結果問人。優點是簡單、
稽核紀錄好寫、真人否決不會浪費已經產生的內容。

ADK 也支援把人放進**流程之內**——用 `LongRunningFunctionTool`，agent 呼叫
工具後整條流程會暫停，等外部把結果送回來才繼續。適合「人的答案會影響 agent
後續怎麼做」的場景（例如主管指定要退多少錢，agent 再據此改寫）。
概念軌與實作軌 Day 15 有完整範例。

## 怎麼看畫面

四張範例工單分別會走到不同結局，值得逐一試：

| 範例 | 預期結果 |
|---|---|
| ① 除濕包詢問（NT$399，語氣平和） | 低風險小額 → **自動放行** |
| ② 耳機瑕疵（NT$4980、VIP、提到消保官） | 三個理由同時觸發 → **擋下** |
| ③ 床包延誤（運送中、有時效壓力） | agent 會呼叫 `check_shipping_status` |
| ④ 查無訂單（還嗆要發文） | 缺事實 → **擋下**，草稿會請客戶提供編號 |

「🔧 工具呼叫軌跡」區塊會顯示 `policy_agent` 實際查了什麼。這一區很重要：
它是「agent 真的去查了」跟「agent 嘴上說有查」的分界線。如果你看到草稿裡
出現軌跡上沒查過的數字，那就是幻覺，該回頭收緊 prompt。

## 已知限制

- **假資料庫**：`tools.py` 裡只有 4 張訂單。接真實系統時把 `lookup_order`
  換成打你的 ERP / 平台 API 即可，agent 那側完全不用改。
- **不會真的寄信**：核准後只寫稽核紀錄。要真的寄，建議把「寄出」也寫成
  Python 而不是工具——理由同上面那張表。
- **分類仍可能錯**：`output_schema` 保證格式正確，不保證判斷正確。所以閘門
  的條件要保守：寧可多擋幾封，不要漏放一封。

## 對應教材

| 主題 | 章節 |
|---|---|
| `output_schema` / 結構化輸出 | 概念軌 `03_models_and_output.ipynb` |
| `FunctionTool` | 概念軌 `02_tools.ipynb`、實作軌 Day 06 |
| Human-in-the-loop | 實作軌 Day 15 |
| Session state | 概念軌 `04_runtime_session.ipynb` |
