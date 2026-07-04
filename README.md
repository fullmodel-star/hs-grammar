# 📐 高中英語文法

一個**離線可用、免安裝、零追蹤**的高中英語**文法**學習 PWA。採「資料 → 建置腳本 → 產出 App」的結構：文法內容存於 `data/`，用 `scripts/` 產生 `app/` 的成品頁。

> 資料全存本機、免註冊、無廣告。

> **狀態**：🔧 本機（英語學習入口 hub 尚未列出上線連結，如已部署可補上）　｜　🟣 主題 `#4338ca`　｜　📱 響應式

---

## 📁 專案結構
| 路徑 | 說明 |
|---|---|
| `app/` | 成品 PWA：`index.html`、`app.template.html`、`manifest.json`、`sw.js`、`icon-*` |
| `data/` | 文法內容與資料：`master.json`、`words6000_raw.json`、`wf_output.json`、`gen/` |
| `scripts/` | 由 `data/` 建置 `app/` 的工具腳本 |

## 🚀 使用
瀏覽器開 `app/index.html` 即可；安裝成 App 需用 https 網址（Android Chrome →「安裝應用程式」，iPhone Safari →「加入主畫面」）。

### 重建（開發用）
內容改在 `data/`，執行 `scripts/` 內的建置腳本重生 `app/` 成品。

## 🔒 隱私
完全離線、不連外部伺服器；學習紀錄只存裝置 `localStorage`；無帳號、無追蹤、無廣告。

## 📝 變更記錄
- 2026-07-05：建立本 README。
- ⚠️ 待確認：是否已上線（hub 連結清單中尚未列出）；若已部署請補上網址並標記納入 hub。
