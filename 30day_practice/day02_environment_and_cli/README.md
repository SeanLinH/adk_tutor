# Day 02 · 武器庫點交：環境建置與 Agents CLI

> 第一部・新兵入伍　|　💻 以 CLI／子程序實跑

## 前置需求

- 🔑 需要 Gemini API 金鑰
- 💻 會用到終端機／子程序

## 今天要學會

1. 用 `adk create` 建出可跑的專案骨架
2. 看懂 ADK 專案的硬性目錄結構
3. 知道 `adk` 與 `agents-cli` 兩條路線的分工

## 📌 文章沒講到、本日補上的部分

- 文章只有 7 行 Python。本日把 CLI 全部**用 subprocess 實跑**，輸出留在 notebook 裡
- 補上 `__init__.py` 忘記寫 `from . import agent` 的實際錯誤訊息
- 補上 `root_agent` 變數名寫錯時會發生什麼

## 檔案

- `day02.ipynb` — 主體

## 對應文章

`Day 02 - 武器庫點交：環境建置與 Agents CLI.md`

---

[← Day 01](../day01_meet_adk2/)　|　[30 天總覽](../README.md)　|　[Day 03 →](../day03_first_agent_and_models/)
