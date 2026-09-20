param([int]$Port = 5000, [switch]$NoBrowser, [switch]$WithoutDemo, [switch]$PrepareOnly)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
function Find-PravaPython([string]$Executable, [string[]]$Prefix = @()) {
    $pravaPreviousPreference = $ErrorActionPreference
    try {
        # Missing optional Python versions are expected during discovery.
        $ErrorActionPreference = 'SilentlyContinue'
        $pravaResult = & $Executable @Prefix -c "import sys; print(sys.executable) if (3,11) <= sys.version_info[:2] < (3,14) else sys.exit(1)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $pravaResult) { return ($pravaResult | Select-Object -Last 1).Trim() }
    } finally { $ErrorActionPreference = $pravaPreviousPreference }
    return $null
}
$pravaPython = $null
$pravaVenv = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (Test-Path -LiteralPath $pravaVenv) {
    $pravaPython = Find-PravaPython $pravaVenv
}
if (-not $pravaPython -and (Get-Command py.exe -ErrorAction SilentlyContinue)) {
    foreach ($pravaVersion in @('3.12', '3.11', '3.13')) {
        $pravaCandidate = Find-PravaPython 'py.exe' @("-$pravaVersion")
        if ($pravaCandidate) { $pravaPython = $pravaCandidate; break }
    }
}
if (-not $pravaPython -and (Get-Command python.exe -ErrorAction SilentlyContinue)) {
    $pravaPython = Find-PravaPython 'python.exe'
}
if (-not $pravaPython) {
    Write-Host 'Install Python 3.12 (64-bit) from https://www.python.org/downloads/windows/ and select Add Python to PATH. Then run START-PRAVA.cmd again.' -ForegroundColor Yellow
    exit 1
}
$pravaArgs = @((Join-Path $PSScriptRoot 'launch.py'), '--port', "$Port")
if ($NoBrowser) { $pravaArgs += '--no-browser' }
if ($WithoutDemo) { $pravaArgs += '--without-demo' }
if ($PrepareOnly) { $pravaArgs += '--prepare-only' }
& $pravaPython @pravaArgs
exit $LASTEXITCODE
