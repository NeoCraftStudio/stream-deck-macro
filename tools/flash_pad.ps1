# Flash one macro pad and prove it works, instead of trusting a silent upload.
#
# Usage:   powershell -ExecutionPolicy Bypass -File tools\flash_pad.ps1
#          powershell ... -Port COM7      (skip auto-detection)
#          powershell ... -SkipMatrix     (flash + handshake only, no key test)
#
# Why this exists: avr109 on the Pro Micro can report success and leave the
# board unprogrammed, and a batch of clones reliably contains boards that
# never enumerate. "No error" is not evidence. Every unit therefore has to
# answer the identity handshake before it counts as flashed.

param(
    [string]$Port,
    [switch]$SkipMatrix
)

$ErrorActionPreference = "Stop"
$raiz   = Split-Path -Parent $PSScriptRoot
$sketch = Join-Path $raiz "firmware\stream_deck_macro.ino"
$cli    = "$env:LOCALAPPDATA\Programs\Arduino IDE\resources\app\lib\backend\resources\arduino-cli.exe"

# The SparkFun FQBN is mandatory, not a preference: the sketch's USB
# descriptors come from whatever board definition compiled it, so this is what
# makes every unit present 1B4F:9206 no matter which bootloader the clone
# shipped with. The 16 MHz processor option is equally mandatory — the default
# is 8 MHz, and flashing a 5V/16MHz board at 8 MHz breaks USB enumeration and
# looks exactly like a dead board.
$fqbn = "SparkFun:avr:promicro:cpu=16MHzatmega32U4"

function Falhar($msg) { Write-Host "FALHOU: $msg" -ForegroundColor Red; exit 1 }
function Ok($msg)     { Write-Host "  ok   $msg" -ForegroundColor Green }
function Passo($msg)  { Write-Host "`n== $msg" -ForegroundColor Cyan }

if (-not (Test-Path $cli))    { Falhar "arduino-cli nao encontrado em $cli" }
if (-not (Test-Path $sketch)) { Falhar "sketch nao encontrado em $sketch" }

Passo "preparando"
# Arduino requires the folder name to match the .ino name; the repo keeps the
# sketch in firmware/ instead, so stage a correctly named copy.
$tmp = Join-Path $env:TEMP "neocraft_flash\stream_deck_macro"
New-Item -ItemType Directory -Force -Path $tmp | Out-Null
Copy-Item $sketch -Destination $tmp -Force
Ok "sketch preparado"

# The companion app grabs the port as soon as the pad answers, which makes the
# upload fail with "access denied". Close it first.
$app = Get-Process | Where-Object { $_.ProcessName -like "*NeoCraft*" }
if ($app) { $app | Stop-Process -Force; Start-Sleep 2; Ok "app fechado (segurava a porta)" }

Passo "detectando a placa"
if (-not $Port) {
    $cand = Get-CimInstance Win32_PnPEntity -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -match "COM(\d+)" -and $_.DeviceID -match "^USB" }
    if (-not $cand) { Falhar "nenhuma placa USB-serial conectada" }
    if (@($cand).Count -gt 1) {
        Write-Host "  mais de uma placa USB-serial:" -ForegroundColor Yellow
        $cand | ForEach-Object { Write-Host ("    {0}" -f $_.Name) }
        Falhar "ambiguo - repita com -Port COMn"
    }
    if ($cand.Name -match "COM(\d+)") { $Port = "COM$($matches[1])" }
}
Ok "usando $Port"

Passo "compilando"
$build = Join-Path $env:TEMP "neocraft_flash\build"
& $cli compile --fqbn $fqbn --build-path $build $tmp | Select-Object -Last 2 | ForEach-Object { Write-Host "  $_" }
if ($LASTEXITCODE -ne 0) { Falhar "erro de compilacao" }
Ok "compilado"

Passo "gravando"
& $cli upload -p $Port --fqbn $fqbn --input-dir $build $tmp | ForEach-Object { Write-Host "  $_" }
if ($LASTEXITCODE -ne 0) { Falhar "erro de gravacao" }
Write-Host "  (upload sem erro - isso ainda NAO prova nada)" -ForegroundColor Yellow

Passo "esperando reenumerar"
# After the 1200 bps touch the board resets and comes back, often on a
# different COM number. Find it again by the VID:PID the sketch now presents.
$novo = $null
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep 1
    $d = Get-CimInstance Win32_PnPEntity -ErrorAction SilentlyContinue |
         Where-Object { $_.DeviceID -match "VID_1B4F&PID_9206" -and $_.Name -match "COM(\d+)" }
    if ($d) { if ($d.Name -match "COM(\d+)") { $novo = "COM$($matches[1])"; break } }
}
if (-not $novo) { Falhar "a placa nao voltou como 1B4F:9206 - gravacao nao pegou" }
Ok "reenumerou em $novo como SparkFun Pro Micro"

Passo "handshake de identidade"
Start-Sleep 2
$s = New-Object System.IO.Ports.SerialPort($novo, 9600, 'None', 8, 'One')
$s.ReadTimeout = 500
$s.DtrEnable = $true
try { $s.Open() } catch { Falhar "nao abriu $novo : $_" }
Start-Sleep 3
$s.DiscardInBuffer()
$s.WriteLine("ID?")
$id = $null
$fim = (Get-Date).AddSeconds(5)
while ((Get-Date) -lt $fim -and -not $id) {
    try { $l = $s.ReadLine().Trim(); if ($l -like "ID:NEOCRAFT_MACRO_DESK*") { $id = $l } } catch { }
}
if (-not $id) { $s.Close(); Falhar "sem resposta ao ID? - o firmware nao esta rodando" }
Ok $id

if ($SkipMatrix) { $s.Close(); Write-Host "`nGRAVADA (teste de matriz pulado)" -ForegroundColor Green; exit 0 }

Passo "teste da matriz - aperte as 16 teclas"
Write-Host "  comece pela 2FX (canto inferior direito), ela tem que dar BTN:15" -ForegroundColor Yellow
Write-Host "  90 s, Ctrl+C para abortar"
$vistos = @{}
$fim = (Get-Date).AddSeconds(90)
while ((Get-Date) -lt $fim -and $vistos.Count -lt 16) {
    try {
        $l = $s.ReadLine().Trim()
        if ($l -match "^BTN:(\d+):DOWN") {
            $n = [int]$matches[1]
            if (-not $vistos.ContainsKey($n)) {
                $vistos[$n] = $true
                Write-Host ("    {0,2}/16  BTN:{1}" -f $vistos.Count, $n)
            }
        }
    } catch { }
}
$s.Close()

if ($vistos.Count -eq 16) {
    Write-Host "`nAPROVADA - 16/16 teclas, handshake ok, $novo" -ForegroundColor Green
    exit 0
}
$faltam = @(0..15 | Where-Object { -not $vistos.ContainsKey($_) })
Write-Host "`nREPROVADA - faltaram: $($faltam -join ', ')" -ForegroundColor Red
Write-Host "Cada numero aponta uma posicao da matriz: conferir solda dessas teclas." -ForegroundColor Yellow
exit 1
