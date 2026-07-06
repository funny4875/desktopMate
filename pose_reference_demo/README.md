# VRM Pose Reference Demo

這是一個獨立範例，用來比較 `pose.json` 套到 `charactor.vrm` 時的 Quaternion 軸向差異。

重點參考 pixiv ChatVRM 的 `VRMAnimation.ts`：

- VRM0 rotation track 會把 quaternion values 中 index 為偶數的分量反號。
- 對 `[x, y, z, w]` 來說，就是 `x` 和 `z` 反號。

## 執行

在此資料夾執行：

```powershell
python -m http.server 8765
```

然後開啟：

```text
http://127.0.0.1:8765/
```

## 使用方式

- 頁面會自動載入 `charactor.vrm` 和內建 `pose.json`。
- 可用 `VRM 模型` 選擇其他 `.vrm` 檔；換模型後會自動重套目前 pose。
- 可按 `載入內建 charactor.vrm` 切回預設模型。
- 可用檔案選擇器改選其他 pose JSON。
- 可按 `讀取線上姿勢清單`，從 Drift Poses 載入縮圖清單。
- 可點縮圖套用，也可用 `選取線上姿勢` 下拉選單搭配 `套用選取姿勢`。
- `JSON 預覽` 會顯示剛讀到的清單 JSON 或單一 pose JSON。
- `套用方式` 預設為 `setNormalizedPose 優先`，用 three-vrm 的 humanoid API 套 normalized pose；也可切回手動 `bone.quaternion` 比較差異。
- `VRM0 quaternion 轉換` 可切換是否套用 `x/z` 反號。
- `略過 head / neck` 可比較頭頸骨骼是否干擾其他控制流程。

## Drift Poses 格式

`https://vrm-pose-filer.pages.dev/out/poselist` 是 Next.js 頁面，不是直接 JSON。
實際清單在：

- `https://vrm-pose-filer.pages.dev/postlist_en.json`
- `https://vrm-pose-filer.pages.dev/postlist.json`

單一 pose 例如 `https://vrm-pose-filer.pages.dev/poses/hello.json` 的格式是：

```json
{
  "vrmMetaVersion": "1",
  "pose": {
    "hips": {
      "position": [0, 0, 0],
      "rotation": [0, 0, 0, 1]
    }
  },
  "expressions": {}
}
```

本範例同時支援：

- `{ "data": { ... }, "vrmVersion": "0" }`
- `{ "pose": { ... }, "vrmMetaVersion": "1" }`
