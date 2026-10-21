# All behavior is shared with Bash through the Python controller.
$ErrorActionPreference = 'Stop'
$controller = Join-Path $PSScriptRoot 'labinf_cli.py'
if (Get-Command python3 -ErrorAction SilentlyContinue) {
    & python3 $controller @args
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 $controller @args
} else {
    Write-Error 'Install Python 3.10 or newer and add it to PATH.'
    exit 1
}
exit $LASTEXITCODE
