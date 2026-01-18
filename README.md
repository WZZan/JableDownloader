# Jable TV & 91Porn 影片下載器

更新v2.0版本 - 使用PyQt5製作UI

## 新功能 (v2.1)

### 🆕 M3U8直接下載功能
- 新增專門的M3U8影片下載功能
- 支援直接輸入M3U8鏈接進行下載
- 自動處理加密M3U8檔案的解密
- 支援多線程下載TS片段並自動合併

## 支援的平台

1. **Jable TV** - 日本成人影片網站
2. **91Porn** - 中文成人影片網站  
3. **M3U8** - 直接下載M3U8格式影片鏈接

## 使用方法

### 啟動應用程式
```bash
python app.pyw
```

### 下載影片
1. 在平台選擇器中選擇對應平台
2. 輸入影片URL或M3U8鏈接
3. 點擊「添加」按鈕
4. 點擊「開始」按鈕開始下載

### M3U8下載說明
- 選擇「M3U8」平台
- 輸入完整的.m3u8鏈接地址
- 系統會自動下載並合併所有TS片段
- 支援AES加密的M3U8檔案

## 檔案結構
```
JableTVDownload/
├── app.pyw              # 主應用程式
├── worker.py            # 下載工作線程（包含M3U8Worker）
├── main_window.py       # 主視窗UI
├── download_item.py     # 下載項目元件
├── crawler.py           # 自定義爬蟲
├── utils.py            # 工具函數
├── config.py           # 配置文件
├── merge.py            # 影片合併
├── delete.py           # 臨時檔案清理
```

## 依賴套件
```bash
uv sync
```
