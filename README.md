# Python VRM Desktop Helper

<img src="desktopmate.png" alt="DesktopMate 角色頭像" width="128">

Windows x64 MSI 安裝程式可從 [Releases](../../releases) 下載；安裝後會建立桌面及開始功能表捷徑。安裝需要系統管理員權限，程式需要 Gemini API 金鑰及網路連線。

維護者建置 MSI：先依下方 Windows 打包步驟產生 `dist/DesktopMate`，安裝 WiX Toolset 4，再執行 `python build_msi.py` 和 `wix build installer.wxs -arch x64 -o DesktopMate.msi`。

這是一個使用 Python (PySide6) + Webview (Three.js/VRM) 實作的 3D 桌面助手。
功能與原版 Electron 版本相同，但使用 Python 作為後端。

## 錄影展示 (Demos)

### 1. 視線追蹤 (LookAt)
角色眼神與頭部會平滑跟隨滑鼠移動：
![LookAt Demo](docs/screenshot_lookat.gif)

### 2. 動態切換姿勢 (Double Click)
左鍵雙擊角色可即時切換不同的 Pose：
![Pose Demo](docs/screenshot_pose.gif)

### 3. 視窗拖拽與滾輪縮放
支援自由移動視窗，並透過滾輪即時縮放角色與視窗大小：
![Zoom Demo](docs/screenshot_zoom.gif)

## 互動教學網頁 (Online Tutorial)
本專案提供詳細的開發教學網頁，請造訪：
[https://ai-ky.github.io/python_vrm_helper/](https://ai-ky.github.io/python_vrm_helper/)

## 功能
- **透明背景與無邊框視窗**：解決 Windows 陰影問題，達成無視窗邊界感。
- **載入 VRM 模型** (`charactor.vrm`)
- **套用 Pose** (`pose.json`)
- **滑鼠互動**：
  - 左鍵拖拽：移動視窗 (觸發物理慣性)
  - 右鍵點擊：開啟 VRMA 動作選單，自動列出 `VRMA/` 資料夾內所有 `.vrma` 動作，點選後只播放一次
  - 右鍵拖拽：旋轉模型
  - 滑鼠滾輪：動態縮放角色與視窗
  - 左鍵雙擊：切換動作
  - 物理效果：移動時模型會有慣性抖動（觸發髮絲等 SpringBone）

## 安裝需求
需安裝 Python 3.10+ 以及 PySide6：

```bash
pip install PySide6
```

## 執行方式
在專案目錄下執行：

```bash
python app.py
```

## 檔案說明
- `app.py`: Python 主程式，負責建立視窗、透明化設定以及透過 QWebChannel 與 JS 溝通。
- `index.html`: 渲染層，使用 Three.js 與 three-vrm 進行 3D 渲染，並處理物理模擬。
- `charactor.vrm`: 預設載入的模型檔案。
- `VRMA/`: 右鍵選單會自動載入此資料夾內的 `.vrma` 動作檔案。
- `pose.json`: 預設載入的姿勢檔案。
- `docs/`: 包含 GitHub Pages 靜態教學網頁與動態演示素材。
- `tools/`: 開發過程中使用的錄影與截圖自動化工具。
- `Implementation_Details.md`: 詳細技術實作報告。

## Gemini 設定與語音聊天

啟動時會先顯示 Gemini 設定視窗。輸入 API Key，按「驗證並取得模型」，
選擇文字對話模型，再按「啟動桌面角色」。驗證失敗時可修改金鑰並重試，
VRM 視窗會在驗證成功及模型選擇完成後才顯示。

角色啟動後會自動聽麥克風，以 Google 語音辨識轉成繁體中文文字，
交給 Gemini 回覆，再顯示文字、朗讀並播放動作。目前沒有文字輸入框。
網路必須可連線到 Google、Gemini 及載入 3D 函式庫的 unpkg。
模型清單驗證成功不代表生成配額充足，實際對話仍受帳戶配額與權限限制。

金鑰與模型選擇儲存在 `%APPDATA%\vrm_desktop_helper\settings.json`，
不包含在原始碼或 Windows 打包檔案中。
程式會停用外部 `SSLKEYLOGFILE` 偵錯記錄設定，以免無效路徑阻止 HTTPS 連線。

## Windows 執行檔打包

已測試的打包環境為 Windows x64 與 Python 3.12：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm DesktopMate.spec
```

也可雙擊 `build_exe.bat`。完成後執行 `dist\DesktopMate\DesktopMate.exe`。
搬移時保留整個 `DesktopMate` 資料夾及 `_internal`，使用者不需要另裝 Python。
`DesktopMate.spec` 包含 VRM、姿勢、VRMA 與提示詞資源，並排除與 Qt
不相容的同名 ICU DLL，讓 Qt 使用 Windows 提供的 ICU。

執行啟動流程測試：

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```
