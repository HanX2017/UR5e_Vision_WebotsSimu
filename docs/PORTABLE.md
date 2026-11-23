# 可攜版與環境重建

## GitHub 原始碼可攜版

目前 repository 採用可重建方式：

- Webots R2023b 由使用者安裝。
- `Setup_Portable.cmd` 在 repository 內建立 `.venv`。
- 套件版本由 `requirements.txt` 固定。
- 控制器的 `runtime.ini` 每次啟動重新產生，寫入目前實際路徑。
- UR5e、PandaHand 與必要資源在 `models/`，世界檔只使用本地相對引用。
- `.venv`、測試輸出、快取與本機 Webots 路徑都被 `.gitignore` 排除。

因此整個資料夾可以移動或重新 clone，不需要修改程式中的絕對路徑。

## 完整內嵌 runtime 版

開發機上另有包含 Python 3.11.8、NumPy、OpenCV、SciPy 的完整封裝，解壓後不需另裝 Python。它已在不同本機路徑、中文／空白路徑和 ZIP 重新解壓環境驗證。

該 ZIP 約 116 MB，超過 GitHub 一般 Git repository 的單檔 100 MB 限制；解壓內容約 415 MB。為避免把大量可再下載的二進位檔寫進 Git 歷史，本 repo 不提交該 runtime。若未來要公開完整封裝，建議改放 GitHub Releases 資產並附 checksum。

## 搬到另一台電腦

1. 安裝 Webots R2023b Windows x64。
2. 安裝 Python 3.11 x64。
3. clone 或下載本 repo，放到可寫入的位置。
4. 執行 `Setup_Portable.cmd`。
5. 執行 `Start_Sorting.cmd`，必要時指定 Webots 路徑。

路徑可以包含空白或中文。若從別台電腦複製了 `config/webots.json`，舊路徑無效時啟動器仍會重新搜尋；也可執行 `Configure_Webots.cmd`。

## 疑難排解

- `Please run Setup_Portable.cmd first`：尚未建立 `.venv`。
- 找不到 Python：確認安裝的是 Python 3.11 x64，並啟用 `py` launcher 或加入 PATH。
- 找不到 Webots：執行 `Configure_Webots.cmd`，選擇 R2023b 安裝資料夾。
- Webots 用錯 Python：不要直接雙擊 `.wbt`；請從本 repo 的 `.cmd` 啟動。
- 想清除環境重建：關閉 Webots 後移除 `.venv`，再執行 `Setup_Portable.cmd`。
