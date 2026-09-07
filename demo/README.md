# Streamlit Demo

兩類 demo，用途不一樣：

| | 檔案 | 目的 |
|---|---|---|
| **概念 demo** | `app_orchestration.py`、`app_coordination.py` | 一支檔案講清楚**一個 ADK 概念**，對應概念軌第 08、09 章 |
| **應用 demo** | 底下四個資料夾 | 一個**中小型電商真的會遇到的問題**，從頭做到能用 |

## 四個電商應用

每個資料夾都是獨立的：`agents.py`（ADK 設計）＋資料/工具＋`app.py`（Streamlit）
＋`README.md`（完整說明）。

| 應用 | 解決什麼 | 主要示範的 ADK 寫法 |
|---|---|---|
| [🛍️ `listing_studio/`](listing_studio/) | 新品上架的內容包（標題/關鍵字/描述/社群貼文） | `SequentialAgent` 包 `ParallelAgent`：扇出扇入 |
| [🎧 `support_triage/`](support_triage/) | 客訴分流與退換貨回覆 | `output_schema` 結構化輸出 + `FunctionTool` + **人工審核閘門** |
| [📦 `inventory_watch/`](inventory_watch/) | 多平台庫存異常日報 | **規則引擎（純 Python）與 LLM 的分界線** |
| [🧭 `campaign_insight/`](campaign_insight/) | 廣告/銷售/庫存交叉分析 | `sub_agents` + `mode="single_turn"`：把 agent 當工具呼叫 |

```bash
uv run streamlit run demo/listing_studio/app.py
uv run streamlit run demo/support_triage/app.py
uv run streamlit run demo/inventory_watch/app.py
uv run streamlit run demo/campaign_insight/app.py
```

四個應用的資料都是假的（`tools.py` / `warehouse.py` / `datasets.py`），
不需要接任何電商平台就能跑完整流程。要接真實資料時，換掉那幾支檔案就好，
agent 那側完全不用改——這也是為什麼它們被拆成獨立檔案。

## 四個應用合起來在講什麼

同一句話問四次：**「這件事該讓誰做？」**

```
       流程固定嗎？
        ├── 是 ──▶ SequentialAgent（順序寫死，可預測）
        │            └── 子步驟彼此獨立嗎？──是──▶ ParallelAgent  ← listing_studio
        └── 否 ──▶ 讓 LLM 決定下一步
                     ├── 要拿回控制權？──▶ mode="single_turn"    ← campaign_insight
                     └── 可以整案移交？──▶ transfer_to_agent     ← app_coordination.py

       這一步是算術還是判斷？
        ├── 算術 ──▶ 寫成 Python                                  ← inventory_watch
        └── 判斷 ──▶ 交給 LLM

       做錯的代價誰承擔？
        └── 公司承擔 ──▶ 加一道人工閘門，而且用 if 不用 prompt    ← support_triage
```

`listing_studio` 與 `campaign_insight` 剛好是同一件事的兩種解法，值得對照著跑：
前者把「三份分析都要做」寫死在流程裡（保證覆蓋率，但不夠靈活），後者讓策略長
自己決定要問誰（靈活，但它偶爾只問一個就下結論）。**這個取捨就是 Orchestration
與 Coordination 的分界。**

## 串流輸出（四個應用都有）

四個應用都用 `RunConfig(streaming_mode=StreamingMode.SSE)` 跑，文字是**逐字長
出來**的，不是等 agent 整段講完才「啪」地跳出來。實作在 `common.py` 的
`StreamPainter`，三件事實測過才知道：

| 事實 | 後果 |
|---|---|
| partial 事件給的是**增量**（一次幾個字），不是累積值 | 要自己接起來，否則畫面上的字會一直閃 |
| partial 事件來得**很密**（一秒十幾個） | Streamlit 每次 `st.markdown()` 都是完整 DOM 重繪，不節流會明顯卡頓 |
| 串流結束後仍會送一個**非 partial 的完整事件** | 收尾用它就好，不必擔心節流漏掉最後幾個字 |
| 同一個 function call 會在 partial 與正式事件**各出現一次** | 工具軌跡只在非 partial 事件收，否則每次呼叫都會記成兩次 |

`output_schema` 的 agent 也能串流——`support_triage` 的分類階段可以看到 JSON
一個欄位一個欄位長出來，而 state 拿到的仍是驗證過的 dict。

### 為什麼限流要用令牌桶

`shared.RateLimiter` 是「每次呼叫之間硬性間隔 60/rpm 秒」，跑 notebook 很合適，
但在互動式 app 上，rpm=10 等於每個 agent 之間插入 6 秒空窗——一條五個 agent
的產線就是 30 秒乾等，串流的意義整個被抵銷。實測時畫面上的文字增長剛好卡在
6.9s、12.6s、18.3s、24.0s 這種等距節奏上，非常明顯。

免費層的限制本來就是「每分鐘 N 次」而不是「每次隔幾秒」，所以 `common.py` 改用
`BurstRateLimiter`（令牌桶）：跑一輪 demo（2~7 次呼叫）完全不用等，只有短時間
內連續重跑才會被擋。同一支 app 實測從 **43 秒縮到 6 秒**。

## `common.py`

四個應用共用的雜務：模型側邊欄、Runner 組裝（含限流 Plugin）、串流緩衝、
卡片與氣泡的 HTML。跟 ADK 概念有關的東西都留在各自的 `agents.py` 裡。

兩支概念 demo 刻意**不**使用 `common.py`——它們的價值是「一個檔案從頭讀到尾」，
拆出去反而看不懂。

## 撞到 429 或 404

- **429（配額）**：免費層是每個模型分開計算配額的，側邊欄換一個模型通常就過了。
  四個應用都掛了 12 RPM 的 `BurstRateLimiter`（`common.py`）。
- **404（模型下架）**：Google 會停用舊模型。若看到
  `models/xxx is no longer available`，檢查 `.env` 的 `ADK_MODEL`，
  或直接在側邊欄選一個候補模型。`shared/config.py` 的 `pick_available_model()`
  可以自動找出還活著的那個。
