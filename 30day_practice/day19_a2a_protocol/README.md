# Day 19 · 跨程序的握手：認識 A2A Protocol

> 第三部・戰術編排　|　🧠 概念為主，附自製可執行實驗

## 前置需求

- 🔑 需要 Gemini API 金鑰

## 今天要學會

1. 說得出什麼時候該用、什麼時候不該用 A2A
2. 描述 ADK 的 A2A 工作流程與三個核心能力
3. 分清楚 A2A 跟「開一個 REST API」到底差在哪

## 📌 文章沒講到、本日補上的部分

- 文章零程式碼。本日用**同程序的 mock** 把 A2A 的三個核心能力演一遍，而且用的是**真的 `a2a` protobuf 型別**（`AgentCard` / `TaskState` / `TaskStatusUpdateEvent`），不是自己捏的 dict
- 補上「A2A vs 直接 HTTP API」的取捨表——這是文章最有價值卻最短的一段
- ⚠️ 補上 A2A 勝過 REST 的真正關鍵：`INPUT_REQUIRED` / `AUTH_REQUIRED` 兩個狀態，**遠端 agent 可以回頭跟你要東西**，而且這是協定的一部分而非各家自訂錯誤碼（notebook 實際跑出這個狀態）
- 補上「什麼時候**不該**用 A2A」四條，以及一張把 Day 06 / 07 / 17 / 19 串起來的連線方式速查表
- ⚠️ 補上 A2A **不含身分驗證**：`AUTH_REQUIRED` 只是狀態值，token 怎麼發怎麼驗還是自己的事（Day 28）

## 檔案

- `day19.ipynb` — 主體

## 對應文章

`Day 19 - 跨程序的握手：認識 A2A Protocol.md`

---

[← Day 18](../day18_collaborative_workflows/)　|　[30 天總覽](../README.md)　|　[Day 20 →](../day20_a2a_exposing_consuming/)
