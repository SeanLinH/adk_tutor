# Day 14 · 資料怎麼流：Data Handling 與 Dynamic Workflows

> 第三部・戰術編排　|　✅ 完整可執行

## 前置需求

- 🔑 需要 Gemini API 金鑰

## 今天要學會

1. 分辨 output / message / state 三個參數
2. 用 Schema 約束節點之間的資料
3. 用 @node 裝飾器與 run_node 寫動態工作流

## 📌 文章沒講到、本日補上的部分

- ⚠️ 補上兩套資料流機制的對照：graph 用 `Event.output`、prebuilt workflow agent 用 `output_key` + state——**混用會出事**
- 補上 `parameter_binding='state'` vs `'node_input'` 的實測差異
- 補上「什麼時候該放棄畫圖改寫程式」的判斷準則

## 檔案

- `day14.ipynb` — 主體

## 對應文章

`Day 14 - 資料怎麼流：Data Handling 與 Dynamic Workflows.md`

---

[← Day 13](../day13_graph_workflows/)　|　[30 天總覽](../README.md)　|　[Day 15 →](../day15_human_in_the_loop/)
