# 系統架構

## 第二階段資料流

```text
sorting_supervisor
  ├─ 依 seed 生成 3～6 顆三色方塊
  ├─ 將相機資訊送給 sorting_vision
  └─ 獨立驗證抓取、落箱與最終分類

sorting_vision
  ├─ 讀取 Camera BGRA 影像
  ├─ HSV／顏色遮罩與輪廓過濾
  ├─ 像素反投影成桌面座標
  └─ 經 Emitter 傳送候選目標

sorting_arm
  ├─ 接收目標顏色與 XY
  ├─ kinematics.py 求解六軸 IK
  ├─ 產生接近、下降、夾取、抬升、搬運、放置路徑
  └─ 讀取關節回授並驅動 PandaHand
```

正式視覺控制與手臂控制不建立 Supervisor，也不讀取物件真值。Supervisor 的角色限定為場景生成與獨立驗收，讓「看見目標」和「檢查答案」分開。

## 主要模組

| 模組 | 責任 |
| --- | --- |
| `sorting/vision.py` | 色彩遮罩、輪廓處理、候選物件計算 |
| `sorting/kinematics.py` | UR5e FK／IK、角度限制與解支選擇 |
| `sorting/comms.py` | 控制器間訊息編解碼 |
| `sorting/scene.py` | 亂數生成條件與場景資料結構 |
| `sorting/settings.py` | JSON 設定載入與檢查 |
| `controllers/sorting_vision/` | 相機控制迴圈與影像輸出 |
| `controllers/sorting_arm/` | 動作狀態機與關節／夾爪控制 |
| `controllers/sorting_supervisor/` | 生成、記錄、成功／失敗驗證 |

## 座標與標定

相機固定於桌面上方並朝下。系統使用已知相機內參、姿態與方塊頂面高度，將輪廓中心像素反投影到固定 Z 平面。這是幾何標定，不含實體鏡頭畸變。

## 抓取策略

每個目標依序經過：`HOME → PREGRASP → DESCEND → CLOSE → LIFT → TRANSIT → PLACE → OPEN → RETREAT`。路徑在執行前求解，關節命令以插值點送出並等待位置回授。夾取靠接觸、摩擦和指爪閉合，不使用 Connector 或直接修改物件座標。

## 第一階段

`vision_controller` 擷取紅色方塊的水平誤差，經低通濾波與 deadband 後送給 `arm_controller`，由基座關節進行跟隨；`test_supervisor` 只負責整合測試與紀錄。
