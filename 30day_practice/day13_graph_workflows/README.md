# Day 13 · 告別失控的 AI：Graph Workflows 與 Graph Routes

> 第三部・戰術編排　|　✅ 完整可執行

> 📌 **建議先讀 [Day 16](../day16_template_workflow_agents/)**：Sequential/Parallel/Loop 是理解圖的墊腳石。

## 前置需求

- 🔑 需要 Gemini API 金鑰

## 今天要學會

1. 用 Workflow + edges 畫出一張執行圖
2. 用 ctx.route 做條件分支
3. 用 JoinNode 做 fan-out / join

## 📌 文章沒講到、本日補上的部分

- ⚠️ 補上文章沒寫清楚的兩件事：節點參數**預設從 state 綁定**（不是上一個節點的回傳值），以及路由靠 **`ctx.route`** 而不是函式回傳值——這兩點寫錯圖就不會動
- 補上「圖的輸出在 `event.output` 不在 `event.content`」
- 補上 Stuck JoinNode 的重現與避免

## 檔案

- `day13.ipynb` — 主體

## 對應文章

`Day 13 - 告別失控的 AI：Graph Workflows 與 Graph Routes.md`

---

[← Day 12](../day12_callbacks_events_plugins/)　|　[30 天總覽](../README.md)　|　[Day 14 →](../day14_data_handling_dynamic_workflows/)
