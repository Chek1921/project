param(
  [ValidateSet('start', 'stop', 'restart', 'status')]
  [string]$Action = 'status'
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$runtimeDir = Join-Path $projectRoot '.runtime'
$python = Join-Path $projectRoot 'venv\Scripts\python.exe'
$services = @(
  @{ Name = 'api'; Match = 'uvicorn api\.main:app'; File = $python; Args = @('-m', 'uvicorn', 'api.main:app', '--host', '127.0.0.1', '--port', '8010', '--reload', '--reload-dir', 'api'); WorkDir = $projectRoot },
  @{ Name = 'worker'; Match = 'worker\.run'; File = $python; Args = @('-m', 'worker.run', '--workers', '4'); WorkDir = $projectRoot },
  @{ Name = 'web'; Match = 'npm run dev'; File = $env:ComSpec; Args = @('/d', '/s', '/c', 'npm run dev -- --host 127.0.0.1'); WorkDir = (Join-Path $projectRoot 'web') }
)

function Get-ServiceProcess($service) {
  $pidFile = Join-Path $runtimeDir "$($service.Name).pid"
  if (-not (Test-Path -LiteralPath $pidFile)) { return $null }
  $servicePid = [int](Get-Content -LiteralPath $pidFile -Raw)
  $process = Get-CimInstance Win32_Process -Filter "ProcessId = $servicePid" -ErrorAction SilentlyContinue
  if ($process -and $process.CommandLine -match $service.Match) { return $process }
  Remove-Item -LiteralPath $pidFile -Force
  return $null
}

function Stop-ProcessTree([int]$processId) {
  Get-CimInstance Win32_Process -Filter "ParentProcessId = $processId" |
    ForEach-Object { Stop-ProcessTree $_.ProcessId }
  Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
}

function Start-Project {
  if (-not (Test-Path -LiteralPath $python)) { throw "Не найден $python. Создайте venv и установите requirements.txt." }
  New-Item -ItemType Directory -Path $runtimeDir -Force | Out-Null
  foreach ($service in $services) {
    if (Get-ServiceProcess $service) { Write-Host "$($service.Name): уже запущен"; continue }
    $process = Start-Process -FilePath $service.File -ArgumentList $service.Args -WorkingDirectory $service.WorkDir `
      -WindowStyle Hidden -RedirectStandardOutput (Join-Path $runtimeDir "$($service.Name).out.log") `
      -RedirectStandardError (Join-Path $runtimeDir "$($service.Name).err.log") -PassThru
    Set-Content -LiteralPath (Join-Path $runtimeDir "$($service.Name).pid") -Value $process.Id
    Write-Host "$($service.Name): запущен (PID $($process.Id))"
  }
}

function Stop-Project {
  foreach ($service in $services) {
    $process = Get-ServiceProcess $service
    if ($process) { Stop-ProcessTree $process.ProcessId; Write-Host "$($service.Name): остановлен" }
    else { Write-Host "$($service.Name): не запущен" }
    $pidFile = Join-Path $runtimeDir "$($service.Name).pid"
    if (Test-Path -LiteralPath $pidFile) { Remove-Item -LiteralPath $pidFile -Force }
  }
}

function Show-Status {
  foreach ($service in $services) {
    $process = Get-ServiceProcess $service
    if ($process) { Write-Host "$($service.Name): работает (PID $($process.ProcessId))" }
    else { Write-Host "$($service.Name): остановлен" }
  }
  Write-Host 'Панель: http://127.0.0.1:5173  API: http://127.0.0.1:8010'
}

switch ($Action) {
  'start' { Start-Project; Start-Sleep -Seconds 2; Show-Status }
  'stop' { Stop-Project }
  'restart' { Stop-Project; Start-Project; Start-Sleep -Seconds 2; Show-Status }
  'status' { Show-Status }
}
