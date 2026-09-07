# 🛍️ 新品上架內容產線

> 賣家丟一句商品資訊 → 賣點分析 → **SEO / 商品描述 / 社群貼文三路並行** → 整合成可直接上架的內容包。

```bash
uv run streamlit run demo/listing_studio/app.py
```

## 這在解什麼問題

中小型電商上一個新品，內容其實要做五、六份：平台標題、搜尋關鍵字、商品描述、
規格 bullet、IG 貼文、FB 貼文。這些工作的共通點是**「知道怎麼做，但沒空做」**——
所以新品往往草草上架，關鍵字亂填、描述沿用供應商的簡體文案、社群貼文乾脆不發。

這條產線把「一件商品的內容包」變成一次執行的產物。它不是要取代人的判斷
（最後那份 `⚠️ 待確認` 區塊就是留給人看的），而是把空白頁變成草稿。

## ADK 設計邏輯

### 架構

```
使用者輸入（商品名稱 / 類別 / 售價 / 筆記）
        ↓
   spec_agent          萃取三個核心賣點、目標客群、競品差異
        ↓  output_key="selling_points"
┌────────── ParallelAgent（content_squad）──────────┐
│  seo_agent        desc_agent        social_agent   │  三路同時開始
│  關鍵字+標題       描述+規格          IG/FB+hashtag   │  彼此看不到對方
└───────┬──────────────┬──────────────────┬─────────┘
   seo_pack        desc_pack          social_pack
        └──────────────┴──────────────────┘
                       ↓
              assemble_agent            挑選 + 整合 + 標出矛盾
                       ↓  output_key="listing_pack"
                  Markdown 上架包
```

### 用到的 ADK 元件

| 元件 | 在這裡的角色 |
|---|---|
| `SequentialAgent` | 最外層的產線骨架，保證「先分析賣點、最後才整合」 |
| `ParallelAgent` | 中間三個內容 agent 同時跑 |
| `output_key` | 每個 agent 把結果寫進 session state |
| instruction 的 `{key}` | 下一階段用 `{selling_points}` 直接把上一階段的輸出注入 prompt |
| `BurstRateLimiter` Plugin | 掛在 Runner 上（見 `demo/common.py`），擋住並行請求打爆免費層 RPM |
| `RunConfig(streaming_mode=SSE)` | 逐字串流，三張卡同時長出文字 |

### 為什麼中間要並行，而不是一路串下去

三份內容**都只依賴賣點分析**，彼此之間沒有先後關係。串成 Sequential 有兩個代價：

1. **慢**：三次模型呼叫從「同時等一次」變成「排隊等三次」。
2. **內容會塌陷**：Sequential 的後段 agent 看得到前段的輸出，社群小編讀到
   商品描述之後，很容易寫出那段描述的改寫版。並行反而保住了三個獨立視角。

反過來說，並行的代價是**分支之間讀不到彼此的 `output_key`**——它們是同時
開始的，`{seo_pack}` 在 `desc_agent` 開跑的當下根本還不存在。所以只要有
「A 的結果要餵給 B」的需求，就必須拆成不同 stage。這條產線的
`assemble_agent` 之所以獨立成第三段，就是這個原因。

### 為什麼第一句話是自然語言，不是 JSON

`build_request()` 把表單欄位組成一段人話再送進去。這是刻意的：產線的第一站
是 LLM，賣家腦中的商品資訊本來就是散的（「客人常問會不會掉炭灰」這種筆記
沒有欄位可以放）。讓 `spec_agent` 讀人話，比逼使用者填滿結構化欄位更貼近
真實情境，也讓「筆記」這個自由欄位能真的影響輸出。

## 怎麼看畫面

- **第 ① 區**跑完後，第 ② 區的**三張卡會同時**從灰色轉為「執行中」——這就是
  `ParallelAgent` 跟 `SequentialAgent` 在畫面上最直觀的差別。
- 三張卡的完成順序**每次都不一樣**（誰先講完看模型回應速度），但第 ③ 區一定
  等三個都完成才開始，這是 `ParallelAgent` 的匯流語義。
- 展開「📨 送進 pipeline 的第一句話」可以看到表單被組成什麼樣子。

## 已知限制

- **賣點是推斷的**：`spec_agent` 對資料不足的地方會標「（推斷）」，但推斷本身
  可能是錯的。上架前該檢查的就是這些。
- **沒有接平台 API**：產出的是 Markdown，還沒有真的打蝦皮/momo 的上架 API。
  要接的話，在 `assemble_agent` 之後加一個帶 `FunctionTool` 的 agent，
  或（更建議）寫成純 Python 的 submit/poll，因為上架 API 是有嚴格 schema
  的非對話式流程。
- **並行會加倍 RPM 壓力**：三路同時送請求，免費層很容易撞 429。
  `demo/common.py` 預設掛了 12 RPM 的 `BurstRateLimiter`（令牌桶），
  跑一輪不會等待，短時間內連續重跑才會被擋。

## 可以往下加的東西

- 多語言版本（跨境電商）：在 `content_squad` 裡再加一個 `translate_agent` 分支。
- 圖片 prompt：加一個分支產出商品情境圖的生成 prompt，再接影像生成 API
  就能真的生圖。
- A/B 版本：把 `assemble_agent` 換成 `LoopAgent`，讓它產出兩版標題再自評。

## 對應教材

| 主題 | 章節 |
|---|---|
| `SequentialAgent` / `ParallelAgent` | 概念軌 `07_workflow_agents.ipynb` |
| `output_key` 與 state 傳遞 | 概念軌 `04_runtime_session.ipynb` |
| Plugin（限流） | 概念軌 `06_app_callbacks_plugins.ipynb`、實作軌 Day 12 |
| 串流輸出 | 實作軌 Day 22（RunConfig 深入） |
