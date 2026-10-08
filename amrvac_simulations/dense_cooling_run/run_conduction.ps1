param([ValidateRange(1, 128)][int]$MpiProcesses = 2)

Set-Location -LiteralPath $PSScriptRoot
$parText = Get-Content -LiteralPath 'amrvac_evolving.par' -Raw -ErrorAction Stop
if ($parText -notmatch 'xprobmin1\s*=\s*0\.01[Dd]0' -or
    $parText -notmatch 'hd_thermal_conduction\s*=\s*\.true\.') {
    throw 'Expected the 0.01 pc inner boundary and enabled thermal conduction.'
}

$outputName = 'conduction_001pc_' + (Get-Date -Format 'yyyyMMdd_HHmmss_fff')
New-Item -ItemType Directory -Path $outputName -ErrorAction Stop | Out-Null
$parText = $parText -replace '(?m)^\s*base_filename\s*=.*$', "        base_filename = '$outputName/test'"
$parPath = Join-Path $PSScriptRoot "$outputName\run.par"
[System.IO.File]::WriteAllText($parPath, $parText.Replace("`r", ''), [System.Text.UTF8Encoding]::new($false))

$wslRun = '/mnt/c/Users/anshm/Projects/GRB modelling/VegasJetFit/amrvac_simulations/dense_cooling_run'
Write-Host "Starting $MpiProcesses MPI ranks; output: $outputName"
wsl -d Ubuntu --cd $wslRun -- env OMP_NUM_THREADS=1 mpirun -np $MpiProcesses ./amrvac -i "$outputName/run.par" 2>&1 |
    Tee-Object -FilePath "$outputName\run.log"
if ($LASTEXITCODE -ne 0) { throw "AMRVAC exited with code $LASTEXITCODE; see $outputName\run.log" }
