# 番茄钟桌面启动器
# 右键 → 使用 PowerShell 运行，或在终端执行: .\启动番茄钟.ps1

$htmlPath = Join-Path $PSScriptRoot "pomodoro-timer.html"

$edgePaths = @(
    "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "C:\Program Files\Microsoft\Edge\Application\msedge.exe"
)
$chromePaths = @(
    "C:\Program Files\Google\Chrome\Application\chrome.exe",
    "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
)

$browser = $null
foreach ($p in $edgePaths + $chromePaths) {
    if (Test-Path $p) { $browser = $p; break }
}

if ($browser) {
    Start-Process $browser "--app=`"$htmlPath`" --window-size=450,680"
} else {
    Start-Process $htmlPath
}
