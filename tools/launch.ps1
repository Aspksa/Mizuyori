# Запуск Mizuyori. Вызывается из Mizuyori.bat.
#
# 1. Ищет Python 3.10+: портативный в папке python, окружение .venv
#    или установленный в системе. Если ничего нет — скачивает портативный.
# 2. Ставит зависимости из requirements.txt (только если файл изменился).
# 3. Запускает main.py.
#
# Файл сохранён в UTF-8 с BOM: иначе Windows PowerShell 5.1 прочитает
# русские буквы неправильно. Все пути обрабатываются как есть (LiteralPath),
# поэтому пробелы, скобки, апострофы и кириллица в пути не мешают.

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12

$ВерсияPython = '3.12.10'

$root      = Split-Path -Parent $PSScriptRoot
$pyDir     = Join-Path $root 'python'
$venvDir   = Join-Path $root '.venv'
$reqFile   = Join-Path $root 'requirements.txt'
$mainFile  = Join-Path $root 'main.py'

$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
$env:PIP_DISABLE_PIP_VERSION_CHECK = '1'

function Сообщить([string]$текст) { Write-Host "[Mizuyori] $текст" }

function Ошибка([string]$текст) {
    Write-Host ''
    Write-Host "[Mizuyori] ОШИБКА: $текст" -ForegroundColor Red
    exit 1
}

# Проверяет, что команда — рабочий Python 3.10+.
# $команда — массив, например @('py', '-3') или @('python').
function Проверить-Python([string[]]$команда) {
    $старое = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $доп = @()
        if ($команда.Length -gt 1) { $доп = $команда[1..($команда.Length - 1)] }
        & $команда[0] @доп -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>$null | Out-Null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    } finally {
        $ErrorActionPreference = $старое
    }
}

function Скачать-Python {
    $arch = 'amd64'
    if ($env:PROCESSOR_ARCHITECTURE -eq 'ARM64' -or $env:PROCESSOR_ARCHITEW6432 -eq 'ARM64') {
        $arch = 'arm64'
    } elseif (-not [Environment]::Is64BitOperatingSystem) {
        $arch = 'win32'
    }
    $url = "https://www.python.org/ftp/python/$ВерсияPython/python-$ВерсияPython-embed-$arch.zip"

    try {
        # Начинаем с чистой папки: остатки прерванной загрузки удаляются
        if ([IO.Directory]::Exists($pyDir)) { [IO.Directory]::Delete($pyDir, $true) }
        [void][IO.Directory]::CreateDirectory($pyDir)
        $web = New-Object Net.WebClient

        Сообщить "Скачиваю портативный Python $ВерсияPython ($arch), около 11 МБ..."
        $zip = Join-Path $pyDir 'python.zip'
        $web.DownloadFile($url, $zip)

        Сообщить 'Распаковываю...'
        Add-Type -AssemblyName System.IO.Compression.FileSystem
        [IO.Compression.ZipFile]::ExtractToDirectory($zip, $pyDir)
        [IO.File]::Delete($zip)

        # Включаем site-packages (нужно для pip) и добавляем папку проекта в sys.path
        $pth = [IO.Directory]::GetFiles($pyDir, 'python*._pth')[0]
        $строки = [IO.File]::ReadAllLines($pth) | ForEach-Object { $_ -replace '^#\s*import site', 'import site' }
        $строки = @($строки) + '..'
        [IO.File]::WriteAllLines($pth, [string[]]$строки, [Text.Encoding]::ASCII)

        Сообщить 'Устанавливаю pip...'
        $getPip = Join-Path $pyDir 'get-pip.py'
        $web.DownloadFile('https://bootstrap.pypa.io/get-pip.py', $getPip)
        & (Join-Path $pyDir 'python.exe') $getPip --no-warn-script-location -q
        if ($LASTEXITCODE -ne 0) { throw "get-pip.py завершился с кодом $LASTEXITCODE" }
        [IO.File]::Delete($getPip)

        [IO.File]::WriteAllText((Join-Path $pyDir '.ready'), $ВерсияPython)
        Сообщить 'Python готов.'
    } catch {
        Ошибка ("не удалось скачать Python: " + $_.Exception.Message + "`n" +
                "           Проверьте интернет или установите Python 3.10+ с python.org`n" +
                "           (галочка «Add Python to PATH») и запустите Mizuyori.bat снова.")
    }
}

$Host.UI.RawUI.WindowTitle = 'Mizuyori'

# ---- 1. Выбираем Python -------------------------------------------------
$python = $null
$envDir = $null

if (Test-Path -LiteralPath (Join-Path $pyDir '.ready')) {
    $python = Join-Path $pyDir 'python.exe'; $envDir = $pyDir
}
elseif (Test-Path -LiteralPath (Join-Path $venvDir 'Scripts\python.exe')) {
    $python = Join-Path $venvDir 'Scripts\python.exe'; $envDir = $venvDir
}
else {
    $системный = $null
    foreach ($вариант in @(@('py', '-3'), @('python'))) {
        if (Проверить-Python $вариант) { $системный = $вариант; break }
    }

    if ($системный) {
        Сообщить 'Создаю виртуальное окружение .venv...'
        $доп = @()
        if ($системный.Length -gt 1) { $доп = $системный[1..($системный.Length - 1)] }
        & $системный[0] @доп -m venv $venvDir
        if ($LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath (Join-Path $venvDir 'Scripts\python.exe'))) {
            $python = Join-Path $venvDir 'Scripts\python.exe'; $envDir = $venvDir
        } else {
            Сообщить 'Не получилось создать .venv, скачаю портативный Python.'
            if ([IO.Directory]::Exists($venvDir)) { [IO.Directory]::Delete($venvDir, $true) }
        }
    } else {
        Сообщить 'Python 3.10+ не найден.'
    }

    if (-not $python) {
        Скачать-Python
        $python = Join-Path $pyDir 'python.exe'; $envDir = $pyDir
    }
}

# ---- 2. Зависимости -----------------------------------------------------
if (Test-Path -LiteralPath $reqFile) {
    $метка = Join-Path $envDir 'requirements.installed'
    $нужноСтавить = $true
    if (Test-Path -LiteralPath $метка) {
        $а = (Get-FileHash -LiteralPath $reqFile).Hash
        $б = (Get-FileHash -LiteralPath $метка).Hash
        $нужноСтавить = ($а -ne $б)
    }
    if ($нужноСтавить) {
        Сообщить 'Устанавливаю зависимости, это может занять минуту...'
        & $python -m pip install -q --no-warn-script-location -r $reqFile
        if ($LASTEXITCODE -ne 0) { Ошибка 'не удалось установить зависимости (подробности выше).' }
        [IO.File]::Copy($reqFile, $метка, $true)
    }
}

# ---- 3. Запуск ----------------------------------------------------------
& $python $mainFile @args
$код = $LASTEXITCODE
if ($код -ne 0) {
    Ошибка "Mizuyori завершился с ошибкой (код $код). Подробности в папке logs."
}
exit 0
