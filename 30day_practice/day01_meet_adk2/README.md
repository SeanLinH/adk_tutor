# Day 01 · 遇見 Google ADK 2.0

> 第一部・新兵入伍　|　🧠 概念為主，附自製可執行實驗

## 前置需求

- 🔑 需要 Gemini API 金鑰

## 今天要學會

1. 說得出 ADK 的核心原語有哪些、彼此怎麼接
2. 解釋為什麼「讓 LLM 當總指揮」會失控
3. 實測 ADK 2.0 的圖形化執行引擎（連單一 agent 都是圖上的節點）
4. 知道 1.x → 2.0 的四個破壞性變更

## 📌 文章沒講到、本日補上的部分

- 文章沒有任何程式碼。本日用**可執行的實驗**證明「2.0 換成圖形執行引擎」：看 traceback 穿過 `workflow/_node_runner.py`、失敗時拋 `DynamicNodeFailError`
- 補上「LLM 當 orchestrator 會無限迴圈」的**可重現 demo**，再用 workflow 修好它
- 補上 1.x / 2.x 的 API 對照表（實際 import 驗證過）

## 檔案

- `day01.ipynb` — 主體

## 對應文章

`Day 01 - 遇見 Google ADK 2.0.md`

---

[30 天總覽](../README.md)　|　[Day 02 →](../day02_environment_and_cli/)
