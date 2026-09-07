# Day 04 · 視覺化戰情室：Runtime、Web UI 與 Visual Builder

> 第一部・新兵入伍　|　💻 以 CLI／子程序實跑

## 前置需求

- 🔑 需要 Gemini API 金鑰
- 💻 會用到終端機／子程序

## 今天要學會

1. 分辨 `adk run` / `adk web` / `adk api_server` 的適用場合
2. 用 `--save_session` / `--resume` / `--replay` 三個互斥選項
3. 把 session 存進 SQLite 並跨程序讀回

## 📌 文章沒講到、本日補上的部分

- 文章零 Python。本日用 subprocess 把每個 CLI 選項**實跑一次**並擷取輸出
- 補上三個 session 選項互斥的實際錯誤訊息
- 補上 `adk web` 的 Caution：官方明示**僅供開發**，不可作為正式服務

## 檔案

- `day04.ipynb` — 主體

## 對應文章

`Day 04 - 視覺化戰情室：Runtime、Web UI 與 Visual Builder.md`

---

[← Day 03](../day03_first_agent_and_models/)　|　[30 天總覽](../README.md)　|　[Day 05 →](../day05_code_with_ai/)
