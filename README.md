# P2P Share — by Stanley Tseng / 史單力

個人版點對點檔案分享工具，以 WebTorrent 技術實現瀏覽器直連傳輸，搭配內建短網址產生器。

**Live Demo**: https://p2p-fileshare-lu3t.onrender.com

---

## 功能特色

- **P2P 直連傳輸** — 檔案透過 WebRTC 在瀏覽器間直接傳輸，不經過伺服器儲存
- **短網址產生** — 自動產生 7 碼短連結，便於分享
- **QR Code** — 即時產生 QR Code，方便手機掃描接收
- **拖放上傳** — 支援多檔案拖放，可逐一移除
- **無需帳號** — 完全免費，不需註冊或登入
- **無檔案大小限制** — 任意格式、任意大小
- **即時監控** — 傳送方可看到連線裝置數、上傳速度、已上傳量
- **下載進度** — 接收方顯示進度條、下載速度、剩餘時間

## 技術架構

```
瀏覽器 (傳送方)                    瀏覽器 (接收方)
  │ client.seed(files)               │
  │ → magnetURI (文字)               │
  │                                  │
  │── POST /api/shorten ──► Flask   │  ← 僅傳 magnet 文字，無檔案位元組
  │   SQLite 儲存短碼對應            │
  │                                  │
  │◄═══════ WebRTC DataChannel ═════►│
  │         檔案直接在瀏覽器間傳輸    │
```

| 元件 | 技術 |
|---|---|
| 後端 | Python / Flask |
| 資料庫 | SQLite（短網址對應） |
| P2P 傳輸 | [WebTorrent.js](https://webtorrent.io) (WebRTC) |
| QR Code | qrcodejs |
| UI | 純 CSS（自訂 citron 黃色系） |
| 部署 | Render.com (免費方案) |

## 本機執行

```bash
# 1. 啟動虛擬環境
source ../.venv/bin/activate

# 2. 安裝相依套件
pip install -r requirements.txt

# 3. 啟動伺服器
python app.py

# 4. 開啟瀏覽器
open http://localhost:5050
```

## 使用方式

**傳送檔案：**
1. 開啟首頁，拖放或點擊選擇檔案
2. 點「建立分享連結」
3. 複製短連結或掃描 QR Code 傳送給接收方
4. **保持此視窗開啟**，直到對方下載完成

**接收檔案：**
1. 開啟分享連結
2. 等待連線建立後自動開始下載
3. 下載完成後點擊下載按鈕儲存

## 部署到 Render

```bash
# 1. Push 到 GitHub
git push github master

# 2. Render 自動偵測並重新部署
# 網址：https://p2p-fileshare-lu3t.onrender.com
```

> **注意**：Render 免費方案閒置 15 分鐘後會 sleep，第一次訪問需等約 30 秒 wake up。

## 隱私說明

- 檔案**不會上傳至任何伺服器**
- 伺服器只儲存 magnet 連結文字（不含檔案內容）
- WebTorrent Tracker 只接收 infohash（檔案指紋），不持有檔案內容
- 關閉傳送方視窗後，連結即自動失效

## 版本

目前版本：**v0.2.0**
詳見 [CHANGELOG.md](CHANGELOG.md)

---

*P2P Share · Powered by [WebTorrent](https://webtorrent.io) · Stanley Tseng / 史單力*
