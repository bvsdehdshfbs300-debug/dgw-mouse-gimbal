param(
    [string]$Cable = 'USB-Blaster [USB-0]'
)

$ErrorActionPreference = 'Stop'

$quartusBin = 'C:\intelFPGA\18.1\quartus\bin64'
$quartusPgm = Join-Path $quartusBin 'quartus_pgm.exe'
if (-not (Test-Path -LiteralPath $quartusPgm)) {
    $quartusPgm = 'quartus_pgm'
}

$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$sof = Join-Path $projectDir 'output_files\mouse_gimbal.sof'

if (-not (Test-Path -LiteralPath $sof)) {
    throw "SOF file not found. Run build.ps1 first."
}

& $quartusPgm -c $Cable -m JTAG -o "p;$sof"
