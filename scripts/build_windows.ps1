$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$AppName = "AgriParameterAnalyzer"
$ExePath = Join-Path $ProjectRoot "dist\$AppName\$AppName.exe"

Set-Location $ProjectRoot

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)]
        [scriptblock]$Command,
        [Parameter(Mandatory = $true)]
        [string]$StepName
    )

    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$StepName failed with exit code $LASTEXITCODE."
    }
}

Write-Host "==> Cleaning old local build artifacts..."
Remove-Item -LiteralPath (Join-Path $ProjectRoot "build") -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath (Join-Path $ProjectRoot "dist") -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath (Join-Path $ProjectRoot "$AppName.spec") -Force -ErrorAction SilentlyContinue

Write-Host "==> Running compile check..."
Invoke-Checked { python -m compileall main.py src tests } "Compile check"

Write-Host "==> Running tests..."
Invoke-Checked { python -m pytest } "Pytest"

Write-Host "==> Running optional real-data formatting smoke test..."
Invoke-Checked { python scripts\smoke_formatting_data.py --default-desktop } "Real-data formatting smoke test"

Write-Host "==> Building Windows directory package with PyInstaller..."
Invoke-Checked { python -m PyInstaller --noconfirm --clean --windowed --name $AppName main.py } "PyInstaller build"

if (-not (Test-Path -LiteralPath $ExePath)) {
    throw "Build completed but executable was not found: $ExePath"
}

Write-Host ""
Write-Host "Build completed."
Write-Host "Executable:"
Write-Host $ExePath
Write-Host ""
Write-Host "For internal testing, distribute the whole folder:"
Write-Host (Join-Path $ProjectRoot "dist\$AppName")
