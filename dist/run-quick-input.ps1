$ErrorActionPreference = "Stop"

$exePath = Join-Path $PSScriptRoot "quick-input.exe"

if (-not (Test-Path -LiteralPath $exePath)) {
    Write-Host "quick-input.exe was not found next to this script." -ForegroundColor Red
    Write-Host "Expected path: $exePath"
    exit 1
}

Write-Host "Running Quick Input from: $exePath"

try {
    Unblock-File -LiteralPath $exePath
    Write-Host "Unblocked quick-input.exe if Windows had marked it as downloaded."
} catch {
    Write-Host "Could not unblock quick-input.exe: $($_.Exception.Message)" -ForegroundColor Yellow
}

Write-Host "Starting quick-input.exe..."
& $exePath @args

$exitCode = $LASTEXITCODE
if ($null -ne $exitCode) {
    Write-Host "quick-input.exe exited with code $exitCode"
    exit $exitCode
}
