# Day 03 · 你的第一個智能助理：Agent 定義與模型設定

> 第一部・新兵入伍　|　✅ 完整可執行

## 前置需求

- 🔑 需要 Gemini API 金鑰

## 今天要學會

1. 用程式碼與 YAML 兩種方式定義 agent
2. 設定 GenerateContentConfig、SafetySetting
3. 用 output_schema 產生結構化輸出
4. 用 LiteLlm 接非 Gemini 模型

## 📌 文章沒講到、本日補上的部分

- 文章把 Agent Config（**Gemini 專用**）跟多模型支援混在一起講，本日拆開釐清
- 補上 `retry_options`——ADK 預設不重試，免費層一定會踩
- 補上 ADK 2.8 實測：`output_schema` 與 `tools` **可以並存**（舊版不行，網路文章多半過時）
- ⚠️ 補上一個容易搞混的地方：`ask()` 的回傳值是 **JSON 字串**，但 `state[output_key]` 是**已 parse 的 dict**——型別不同，驗證方法也不同

## 檔案

- `day03.ipynb` — 主體

## 對應文章

`Day 03 - 你的第一個智能助理：Agent 定義與模型設定.md`

---

[← Day 02](../day02_environment_and_cli/)　|　[30 天總覽](../README.md)　|　[Day 04 →](../day04_runtime_web_ui/)
