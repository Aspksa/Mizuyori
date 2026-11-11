# Downloads portable (embeddable) Python into <project>\python
# and installs pip into it. Called by Mizuyori.bat.
# ASCII-only on purpose (Windows PowerShell 5.1 reads BOM-less files as ANSI).
# All paths are handled with literal .NET APIs, so spaces, brackets,
# apostrophes and Cyrillic letters in the folder path are safe.

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12

$PyVersion = '3.12.10'

$root  = Split-Path -Parent $PSScriptRoot
$pyDir = Join-Path $root 'python'

$arch = 'amd64'
if ($env:PROCESSOR_ARCHITECTURE -eq 'ARM64' -or $env:PROCESSOR_ARCHITEW6432 -eq 'ARM64') {
    $arch = 'arm64'
} elseif (-not [Environment]::Is64BitOperatingSystem) {
    $arch = 'win32'
}
$url = "https://www.python.org/ftp/python/$PyVersion/python-$PyVersion-embed-$arch.zip"

try {
    # Start clean: a half-finished previous attempt is removed
    if ([IO.Directory]::Exists($pyDir)) { [IO.Directory]::Delete($pyDir, $true) }
    [void][IO.Directory]::CreateDirectory($pyDir)

    $web = New-Object Net.WebClient

    Write-Host "[Mizuyori] Downloading Python $PyVersion ($arch)..."
    $zip = Join-Path $pyDir 'python.zip'
    $web.DownloadFile($url, $zip)

    Write-Host '[Mizuyori] Unpacking...'
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [IO.Compression.ZipFile]::ExtractToDirectory($zip, $pyDir)
    [IO.File]::Delete($zip)

    # Enable site-packages (needed for pip) and add the project folder to sys.path
    $pth = [IO.Directory]::GetFiles($pyDir, 'python*._pth')[0]
    $lines = [IO.File]::ReadAllLines($pth) | ForEach-Object { $_ -replace '^#\s*import site', 'import site' }
    $lines = @($lines) + '..'
    [IO.File]::WriteAllLines($pth, [string[]]$lines, [Text.Encoding]::ASCII)

    Write-Host '[Mizuyori] Installing pip...'
    $getPip = Join-Path $pyDir 'get-pip.py'
    $web.DownloadFile('https://bootstrap.pypa.io/get-pip.py', $getPip)
    & (Join-Path $pyDir 'python.exe') $getPip --no-warn-script-location -q
    if ($LASTEXITCODE -ne 0) { throw "get-pip.py failed (exit code $LASTEXITCODE)" }
    [IO.File]::Delete($getPip)

    [IO.File]::WriteAllText((Join-Path $pyDir '.ready'), $PyVersion)
    Write-Host '[Mizuyori] Python is ready.'
    exit 0
}
catch {
    Write-Host ''
    Write-Host "[Mizuyori] ERROR: $($_.Exception.Message)"
    Write-Host '[Mizuyori] Check the internet connection, or install Python 3.10+ from python.org'
    Write-Host '           (tick "Add Python to PATH") and run Mizuyori.bat again.'
    exit 1
}
