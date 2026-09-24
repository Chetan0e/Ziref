$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$RootDir = Split-Path -Parent $ScriptDir
& "$RootDir\.venv\Scripts\python.exe" -m packages.cli.main $args
