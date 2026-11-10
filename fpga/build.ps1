$ErrorActionPreference = 'Stop'

$quartusBin = 'C:\intelFPGA\18.1\quartus\bin64'
$quartusSh = Join-Path $quartusBin 'quartus_sh.exe'
if (-not (Test-Path -LiteralPath $quartusSh)) {
    $quartusSh = 'quartus_sh'
}

$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Push-Location $projectDir
try {
    & $quartusSh --flow compile mouse_gimbal
} finally {
    Pop-Location
}
