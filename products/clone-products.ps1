$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

Import-Csv (Join-Path $Root "products/repositories.tsv") -Delimiter "`t" | ForEach-Object {
    $Target = Join-Path $Root $_.directory
    if (Test-Path (Join-Path $Target ".git")) {
        Write-Host "exists: $($_.directory)"
    } else {
        git clone $_.remote $Target
    }
}
