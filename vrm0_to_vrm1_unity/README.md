# VRM0 to VRM1 Unity Converter

This Unity project is prepared to convert:

```text
../charactor.vrm
```

into:

```text
../charactor_vrm1.vrm
```

It uses UniVRM `0.131.1` from the local checkout at:

```text
../.tmp_univrm_v0_131_1/Packages
```

## Requirements

- Unity Editor 2022.3 LTS or newer.
- UniVRM packages are already referenced through `Packages/manifest.json`.

## Run In Unity UI

1. Open this folder as a Unity project.
2. Wait for packages to resolve and scripts to compile.
3. Run `Tools > VRM > Convert ../charactor.vrm to VRM1`.

## Run In Batch Mode

Replace the Unity path with the installed editor path:

```powershell
& "C:\Program Files\Unity\Hub\Editor\2022.3.62f1\Editor\Unity.exe" `
  -batchmode `
  -quit `
  -projectPath "C:\Users\ky\Desktop\python_vrm_helper-master\vrm0_to_vrm1_unity" `
  -executeMethod Vrm0ToVrm1BatchConverter.ConvertDefault `
  -logFile "C:\Users\ky\Desktop\python_vrm_helper-master\vrm0_to_vrm1_unity\convert.log"
```

## License Note

UniVRM requires explicit VRM1 meta/license fields for public migration. This script uses restrictive defaults:

- avatar permission: only author
- credit notation: required
- redistribution: false
- modification: prohibited

Adjust `Assets/Editor/Vrm0ToVrm1BatchConverter.cs` if you have rights to use different license settings.
