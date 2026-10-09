param([ValidateRange(1, 128)][int]$MpiProcesses = 2)

$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$parText = Get-Content -LiteralPath 'amrvac_evolving.par' -Raw
$suiteName = 'resolution_' + (Get-Date -Format yyyyMMdd_HHmmss_fff)
$wslRun = '/mnt/c/Users/anshm/Projects/GRB modelling/VegasJetFit/amrvac_simulations/dense_cooling_run'

# Run all three from the problem directory so the same wind table is read.
# Only domain_nx1 and the output destination differ among these inputs.
foreach ($cells in @(192, 384, 768)) {
    $casePath = "$suiteName/nx$cells"
    New-Item -ItemType Directory -Path $casePath | Out-Null
    $caseText = $parText -replace '(?m)^\s*domain_nx1\s*=.*$', "        domain_nx1=$cells"
    $caseText = $caseText -replace '(?m)^\s*base_filename\s*=.*$', "        base_filename = '$casePath/test'"
    $parPath = Join-Path $PSScriptRoot "$casePath/run.par"
    [System.IO.File]::WriteAllText($parPath, $caseText.Replace("`r", ''), [System.Text.UTF8Encoding]::new($false))
    $command = "wsl -d Ubuntu --cd '$wslRun' -- env OMP_NUM_THREADS=1 mpirun -np $MpiProcesses ./amrvac -i '$casePath/run.par' 2>&1 | Tee-Object -FilePath '$casePath/run.log'"
    Write-Host $command
    Add-Content -LiteralPath "$suiteName/commands.ps1" -Value $command
}
Write-Host "Prepared $suiteName. Run its commands separately; preparation does not start simulations."
