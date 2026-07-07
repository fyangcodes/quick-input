$ErrorActionPreference = "Stop"

$exePath = Join-Path $PSScriptRoot "quick-input.exe"

Write-Host "Quick Input diagnostic"
Write-Host "Folder: $PSScriptRoot"
Write-Host ""

Write-Host "Windows / machine"
Write-Host "  OS: $([System.Environment]::OSVersion.VersionString)"
Write-Host "  64-bit OS: $([System.Environment]::Is64BitOperatingSystem)"
Write-Host "  64-bit PowerShell process: $([System.Environment]::Is64BitProcess)"
try {
    $computerInfo = Get-ComputerInfo
    Write-Host "  OS architecture: $($computerInfo.OsArchitecture)"
    Write-Host "  Windows product: $($computerInfo.WindowsProductName)"
} catch {
    Write-Host "  Get-ComputerInfo unavailable: $($_.Exception.Message)"
}
Write-Host ""

if (-not (Test-Path -LiteralPath $exePath)) {
    Write-Host "quick-input.exe was not found next to this script." -ForegroundColor Red
    Write-Host "Expected path: $exePath"
    exit 1
}

$file = Get-Item -LiteralPath $exePath
$hash = Get-FileHash -LiteralPath $exePath -Algorithm SHA256

Write-Host "Executable file"
Write-Host "  Path: $exePath"
Write-Host "  Size: $($file.Length) bytes"
Write-Host "  SHA256: $($hash.Hash)"
Write-Host "  Zone identifier present: $(Test-Path -LiteralPath ($exePath + ':Zone.Identifier'))"

$bytes = [System.IO.File]::ReadAllBytes($exePath)
if ($bytes.Length -lt 0x40) {
    Write-Host "  Result: file is too small to be a valid Windows executable." -ForegroundColor Red
    exit 1
}

$mz = [System.Text.Encoding]::ASCII.GetString($bytes, 0, 2)
if ($mz -ne "MZ") {
    Write-Host "  Result: missing MZ header. This is not a normal Windows .exe file." -ForegroundColor Red
    exit 1
}

$peOffset = [BitConverter]::ToInt32($bytes, 0x3C)
if ($peOffset -lt 0 -or $bytes.Length -lt ($peOffset + 6)) {
    Write-Host "  Result: broken PE header offset. The file is probably corrupted/incomplete." -ForegroundColor Red
    exit 1
}

$peSignature = [System.Text.Encoding]::ASCII.GetString($bytes, $peOffset, 4)
if ($peSignature -ne "PE`0`0") {
    Write-Host "  Result: missing PE signature. The file is probably corrupted/incomplete." -ForegroundColor Red
    exit 1
}

$machine = [BitConverter]::ToUInt16($bytes, $peOffset + 4)
$machineName = switch ($machine) {
    0x014c { "x86 / 32-bit" }
    0x8664 { "x64 / AMD64" }
    0xAA64 { "ARM64" }
    default { "unknown machine type 0x{0:X4}" -f $machine }
}

Write-Host "  PE machine type: $machineName"
Write-Host ""

if ($machine -eq 0x8664 -and -not [System.Environment]::Is64BitOperatingSystem) {
    Write-Host "Result: this is a 64-bit EXE, but Windows is 32-bit. Rebuild a 32-bit EXE." -ForegroundColor Red
    exit 1
}

Write-Host "Result: the EXE header looks valid for this machine." -ForegroundColor Green
Write-Host "If it still fails, compare the size and SHA256 with the working PC, then try run-quick-input.ps1."
