# Jable TV / 91Porn / M3U8 影片下載器（Web 版）

以 [NiceGUI](https://nicegui.io/) 打造的網頁版下載器,支援多任務並行下載、自動解密合併。

## 支援平台

1. **Jable TV** — 自動解析頁面取得 m3u8
2. **91Porn** — 自動解析加密頁面取得影片源
3. **M3U8** — 直接輸入 m3u8 連結下載(支援 master 主清單、AES 加密)

## 環境需求

- Python >= 3.10
- [uv](https://docs.astral.sh/uv/)(套件/環境管理)
- 影片合併需要系統已安裝 `ffmpeg`(在 PATH 中)

## 安裝

```bash
uv sync
```

## 啟動

### 前景執行（看 log、本機開發）
```bash
uv run jable-web
```
啟動後開瀏覽器:<http://localhost:8000>

### 背景常駐（推薦：SSH 遠端、斷線不中斷下載）
透過 WMI 建立脫離 SSH session 的行程,網路斷線時 PC 上的下載不會中斷。

```powershell
.\scripts\start_web.ps1      # 背景啟動，log 寫入 web.log、PID 記於 web.pid
Get-Content web.log -Wait    # 隨時查看即時進度（Ctrl+C 只離開檢視，不影響下載）
.\scripts\stop_web.ps1       # 停止服務
```

## 使用方式

1. 選擇平台(或用 `Auto` 自動判斷)
2. 貼上影片網址或 `.m3u8` 連結
3.（可選)設定儲存位置、自訂檔名、同時下載數
4.「➕ 加入佇列」→ 系統自動下載 TS 片段、解密、合併為 mp4

下載路徑於 `settings.json` 設定(`jav_paths` / `shortvideo_paths`,依優先序取第一個存在的路徑)。

## 專案結構

```
JableDownloader/
├── src/jabledownloader/      # 下載核心套件
│   ├── web_app.py            # NiceGUI web 入口（jable-web）
│   ├── core.py               # 各平台下載流程
│   ├── crawler.py            # 多執行緒 TS 抓取
│   ├── merge.py              # 合併 TS → mp4
│   ├── delete.py             # 清理暫存
│   ├── config.py             # HTTP headers
│   └── settings_manager.py   # 下載路徑設定
├── scripts/                  # 背景常駐維運腳本
│   ├── start_web.ps1
│   └── stop_web.ps1
├── settings.json             # 下載路徑設定
└── pyproject.toml
```
