$ErrorActionPreference = "Stop"

$projectPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$workspacePath = Split-Path -Parent $projectPath
$logPath = Join-Path $projectPath "convert.log"

$unityCandidates = @()
$hubEditorRoot = "C:\Program Files\Unity\Hub\Editor"
if (Test-Path $hubEditorRoot) {
    $unityCandidates += Get-ChildItem $hubEditorRoot -Directory |
        Sort-Object Name -Descending |
        ForEach-Object { Join-Path $_.FullName "Editor\Unity.exe" }
}

$pathUnity = Get-Command Unity.exe -ErrorAction SilentlyContinue
if ($pathUnity) {
    $unityCandidates += $pathUnity.Source
}

$unityExe = $unityCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $unityExe) {
    throw "Unity.exe was not found. Install Unity Editor 2022.3 LTS or newer, then rerun this script."
}

Write-Host "Unity: $unityExe"
Write-Host "Project: $projectPath"
Write-Host "Input: $(Join-Path $workspacePath 'charactor.vrm')"
Write-Host "Output: $(Join-Path $workspacePath 'charactor_vrm1.vrm')"
Write-Host "Log: $logPath"

& $unityExe `
    -batchmode `
    -quit `
    -projectPath $projectPath `
    -executeMethod Vrm0ToVrm1BatchConverter.ConvertDefault `
    -logFile $logPath

$exitCode = $LASTEXITCODE
if ($exitCode -ne 0) {
    throw "Unity conversion failed with exit code $exitCode. See log: $logPath"
}

$outputPath = Join-Path $workspacePath "charactor_vrm1.vrm"
if (-not (Test-Path $outputPath)) {
    throw "Unity exited successfully, but output was not found: $outputPath"
}

Get-Item $outputPath | Select-Object FullName, Length, LastWriteTime
