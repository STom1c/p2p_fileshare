# Changelog

所有版本變更記錄。格式依照 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.0.0/)，版本號遵循 [Semantic Versioning](https://semver.org/)。

---

## [0.3.0] - 2026-02-28

### Added
- 自架 WebTorrent Tracker（`bittorrent-tracker`）部署於 Render，確保 WebRTC 信令中繼可靠運作
- Tracker 連線診斷：頁面載入時自動檢測各 tracker 可達性，結果輸出至 Console
- `tracker/` 子目錄：包含 Node.js tracker 伺服器及 package.json
- `render.yaml` 新增第二個 Render web service（`p2p-share-tracker`）

### Fixed
- 修正 Tracker 連線問題：自架 tracker 作為首要信令伺服器，公共 tracker 保留為備用
- 移除已停用的 `tracker.btorrent.xyz`

### Changed
- Tracker 清單優先順序調整：自架 > openwebtorrent.com > webtorrent.dev > files.fm

---

## [0.2.0] - 2026-02-27

### Changed
- 背景色改為暖柑橙萊姆黃 `#D2CB35` citron 色系
- 主色按鈕改為深森林綠 `#2a5500`，配合亮色背景對比
- 卡片、統計欄位、輸入框改為半透明白色玻璃態
- 導覽列改為半透明深黃綠

### Fixed
- 「拖拽」文字統一改為「拖放」（更符合中文慣用詞）

### Added
- 導覽列與頁尾加入品牌標示 `by Stanley Tseng / 史單力`
- 頁面 title 更新為 `P2P Share by Stanley Tseng / 史單力`

---

## [0.1.0] - 2026-02-27

### Added
- 初始版本發布
- Flask 後端 + SQLite 短網址產生器（7 碼英數短碼）
- WebTorrent.js P2P 檔案傳輸（WebRTC，不經過伺服器）
- 拖放多檔案上傳支援
- QR Code 自動產生（qrcodejs）
- 即時傳輸統計（連線裝置數、上傳速度、已上傳量）
- 接收頁面含進度條、下載速度、剩餘時間估算
- 深色玻璃態 UI 設計
- 傳送方關閉視窗前的確認警告
- 404 錯誤頁面
- Render 部署設定（`Procfile`、`render.yaml`）
- 部署至 Render：https://p2p-fileshare-lu3t.onrender.com
