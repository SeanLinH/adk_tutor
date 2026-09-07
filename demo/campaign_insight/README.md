# 🧭 檔期成效交叉分析

> 「這波雙 11 到底有沒有賺？」→ 策略長 agent 把**廣告 / 銷售 / 庫存**三位分析師
> 各問一次 → 交叉比對三份數據 → 給出下週的預算調整建議。

```bash
uv run streamlit run demo/campaign_insight/app.py
```

## 這在解什麼問題

檔期結束後的覆盤，中小電商通常只看一個數字：ROAS。而這個 demo 的假資料
刻意設計成**單看任何一份資料都會下錯結論**：

| 只看這份 | 會得到的結論 | 為什麼錯 |
|---|---|---|
| 廣告 | ROAS 4.0，花 18 萬帶回 72 萬 → **加碼** | 沒扣掉折扣與成本 |
| 銷售 | 營收 72 萬，成長不錯 | 平均折扣 32%、毛利率 18% → 毛利 12.96 萬 **< 廣告費 18 萬** |
| 庫存 | SKU-1004 剩 3.2 天可售 | 單看不知道廣告正在推它 |

正確的結論要三份資料**對照**才看得出來：這檔實際是賠的，而且廣告主推的
充電器（毛利率只有 11%）三天後就會斷貨、補貨要 21 天——接下來每一塊廣告費
都在把人送到一個買不到東西的頁面。該做的是把預算移到毛利 34% 的耳機。

## ADK 設計邏輯

### 架構

```
使用者問題
     ↓
 strategist（chat 模式）
     │  三位分析師以 sub_agents 掛上，各自 mode="single_turn"
     │  → ADK 自動把它們變成 strategist 可以呼叫的工具
     ├──▶ ads_analyst   ─ get_ad_metrics    ─┐
     ├──▶ sales_analyst ─ get_sales_metrics ─┤ 每位只看得到自己的資料源
     ├──▶ stock_analyst ─ get_stock_levels  ─┘
     ↓  三份回答都回到 strategist 手上
 交叉比對 → 結論 + 下週行動
```

### 核心：控制權會不會回來

ADK 有三種把 agent 接起來的方式，差別只有這一句：

| 寫法 | 呼叫後控制權 | 像什麼 | 這個 repo 裡的例子 |
|---|---|---|---|
| `sub_agents`（預設 `mode="chat"`）+ `transfer_to_agent` | **交出去，不回來** | 把案子轉給別的部門 | `demo/app_coordination.py` |
| `sub_agents` + `mode="single_turn"` | 答完**回到 caller** | 打電話問專家，掛掉繼續做事 | **本 demo** |
| `AgentTool(agent=...)` | 同上，但跑在**獨立 runner/session** | 外包給另一家公司 | （不建議，見下） |

這個應用要的是「問完三個人，自己下結論」——如果用 transfer，策略長把問題轉給
廣告分析師之後就再也拿不回控制權，也就沒有人能做交叉比對了。

### 為什麼不用 `AgentTool`

ADK 2.x 的 `AgentTool` docstring 已經明講
*"Direct usage of AgentTool is discouraged"*，建議改用 `mode="single_turn"`。
實際差別看原始碼很清楚：

- `AgentTool.run_async()` 會**另外 new 一個 `Runner` 跟 `InMemorySessionService`**
  去跑子 agent → 子 agent 的事件不會回到外層串流。畫面上只看得到「呼叫了
  ads_analyst」跟「它回了一段話」，看不到它到底有沒有真的去查資料。
- `mode="single_turn"` 走 `tool_context.run_node()`，跑在**同一個 invocation**
  裡 → 分析師自己的 `get_ad_metrics` 呼叫也會出現在事件串流上。

所以右側的「諮詢與查詢軌跡」能同時顯示兩層：策略長問了誰、那個人又查了什麼。
這在 debug「數字是哪來的」時差很多。

### 為什麼每位分析師只給一把鑰匙

`ads_analyst` 只有 `get_ad_metrics`，拿不到銷售與庫存資料。這個限制是刻意的：

1. **它不可能「順便」評論別的領域**——沒有資料就編不出數字（能編的空間小很多）。
2. **責任可追溯**：畫面上每個數字都能對到是哪位分析師講的、他查了哪個工具。
3. 交叉比對只能發生在 strategist 那一層，也就是**唯一一個看得到全貌的地方**。

instruction 裡也明講「被問到不是你領域的事，就說去問別人」——這比單純不給工具
更保險一點。

## 怎麼看畫面

- 右側軌跡有兩種顏色：**彩色的是「策略長諮詢某位分析師」**，
  **灰色 monospace 的是「某位分析師呼叫資料工具」**。
- 展開下方「三份原始資料」可以自己核對——agent 講的數字有沒有出現在表裡。
  這是最實用的驗收方式。
- 如果某一輪 strategist 只問了一兩位分析師，畫面會跳出提醒。這是「讓 LLM
  自己決定要問誰」的真實代價：它有時候覺得問一個就夠了。要保證每份資料
  都被看過，就得改用 `ParallelAgent` 把三份分析寫死成必經步驟
  （見 `demo/listing_studio/`）。**這個取捨本身就是 Coordination 與
  Orchestration 的分界。**

## 已知限制

- **假資料是靜態的**：`datasets.py` 就是一組寫死的數字。接真實資料時，把三個
  工具換成打 Meta Ads API / 你的訂單資料庫 / 庫存系統即可，agent 那側不用改。
- **歸因是簡化的**：`attributed_revenue` 直接用平台回報的歸因營收，沒有處理
  跨渠道重複歸因——實務上三個平台的歸因加起來常常大於實際營收。
- **不保證問滿三位**：見上。要保證覆蓋率就別用這個模式。
- **數字會有小幅漂移**：instruction 明講「只能使用分析師回報的數字」，但實測
  仍會看到策略長把「歸因營收 396,000」寫成「約 395,720」（它自己拿花費 ×
  ROAS 重算了一次）。結論方向不受影響，但這正是為什麼原始資料表要放在同一頁
  上——**能核對的數字才是能用的數字**。

## 對應教材

| 主題 | 章節 |
|---|---|
| 多 agent 協作與 transfer | 概念軌 `09_coordination.ipynb`、實作軌 Day 17 |
| Agent 當工具用 | 概念軌 `08_orchestration.ipynb`、實作軌 Day 18 |
| `FunctionTool` | 概念軌 `02_tools.ipynb` |
| 串流輸出（RunConfig） | 實作軌 Day 22 |
