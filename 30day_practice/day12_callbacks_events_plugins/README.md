# Day 12 · 事件驅動架構：Callbacks、Events 與 Plugins

> 第二部・裝備升級　|　✅ 完整可執行

## 前置需求

- 🔑 需要 Gemini API 金鑰

## 今天要學會

1. 解剖 Event 的結構與 Event Loop 的接力方式
2. 用好六個 callback 掛載點
3. 分辨什麼該寫成 Plugin、什麼該寫成 Callback

## 📌 文章沒講到、本日補上的部分

- 文章只有 17 行程式碼，是**補充空間最大的一天**
- ⚠️ 核心補充：把「**Plugin callback 一定先於物件 callback，而且會短路它**」寫成可執行的順序驗證實驗——這條規則光看字很容易記反
- ⚠️ 實測發現：**before 和 after 都是 Plugin 先**，不像一般中介層那樣「進去 A→B、出來 B→A」。想在 agent 的 after_tool 改寫結果，Plugin 已經先看過了
- 補上「你的稽核 callback 可能一次都沒被呼叫，而且不會報錯」的實例
- ⚠️ 護欄最危險的失敗方式：`tool.name` 比對打錯字 → 條件永遠 False → 護欄形同不存在，而且完全不報錯

## 檔案

- `day12.ipynb` — 主體

## 對應文章

`Day 12 - 事件驅動架構：Callbacks、Events 與 Plugins.md`

---

[← Day 11](../day11_caching_and_artifacts/)　|　[30 天總覽](../README.md)　|　[Day 13 →](../day13_graph_workflows/)
