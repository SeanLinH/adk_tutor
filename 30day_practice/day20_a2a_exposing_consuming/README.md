# Day 20 · 動手接上遠端 Agent：A2A Exposing 與 Consuming

> 第三部・戰術編排　|　🔀 需要兩個程序（notebook 自動起停）

## 前置需求

- 🔑 需要 Gemini API 金鑰
- 📦 需要額外套件或服務

## 今天要學會

1. 用 to_a2a() 把 agent 變成服務
2. 用 RemoteA2aAgent 消費遠端 agent
3. 讀懂 agent card

## 📌 文章沒講到、本日補上的部分

- 需要兩個程序。本日用背景 subprocess 起 server、notebook 當 client，結尾自動清理
- 補上 agent card 的**實際內容**（用 HTTP 抓下來印出），文章只有示意；並逐欄對照它是從 agent 的哪個屬性自動產生的
- ⚠️ 補上**本日最重要的坑**：`127.0.0.1` 與 `localhost` 對 A2A 是**不同 origin**，不一致就連不上，而且是**靜默失敗**——`ask()` 回空字串、不拋例外，真正的錯誤藏在 `event.error_message`（notebook 實際重現）
- ⚠️ 補上安全提醒：**每個 tool 都會變成 agent card 上的一個 skill**，工具的 docstring 等於對外公開文件
- 補上本地 + 遠端混合委派時的事件串流長相——兩者的 `transfer_to_agent` 格式完全相同

## 檔案

- `day20.ipynb` — 主體

## 對應文章

`Day 20 - 動手接上遠端 Agent：A2A Exposing 與 Consuming.md`

---

[← Day 19](../day19_a2a_protocol/)　|　[30 天總覽](../README.md)　|　[Day 21 →](../day21_live_and_voice/)
