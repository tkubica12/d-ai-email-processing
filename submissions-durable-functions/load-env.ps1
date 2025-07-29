# load-env.ps1 
# Simple script to load environment variables from local.settings.json
# Usage: . .\load-env.ps1

$localSettings = Get-Content ".\local.settings.json" -Raw | ConvertFrom-Json
$localSettings.Values.PSObject.Properties | ForEach-Object {
    [Environment]::SetEnvironmentVariable($_.Name, $_.Value, "Process")
}
Write-Host "Environment variables loaded from local.settings.json" -ForegroundColor Green
