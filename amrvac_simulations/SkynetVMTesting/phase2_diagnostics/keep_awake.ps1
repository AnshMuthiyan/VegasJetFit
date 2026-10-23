# Purpose: Temporarily prevent automatic idle sleep during local validation, without holding the display awake or changing a power plan.
param(
    [Parameter(Mandatory=$true)][string]$ControlDir,
    [ValidateRange(1,12)][int]$MaximumHours=6
)
$ErrorActionPreference='Stop'
$taskControlPath=[IO.Path]::GetFullPath($ControlDir)
[IO.Directory]::CreateDirectory($taskControlPath) | Out-Null
$taskLog=Join-Path $taskControlPath 'power_request.log'
'# Purpose: Record the bounded validation-only automatic-sleep prevention request.' | Set-Content -LiteralPath $taskLog
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class AMRVACTestPower {
    [DllImport("kernel32.dll", SetLastError=true)]
    public static extern UInt32 SetThreadExecutionState(UInt32 flags);
}
'@
$taskDeadline=[DateTime]::UtcNow.AddHours($MaximumHours)
try {
    $taskPrevious=[AMRVACTestPower]::SetThreadExecutionState([uint32]2147483649)
    if ($taskPrevious -eq 0) { throw 'Windows refused the temporary system execution-state request.' }
    @{purpose='Identify the temporary validation power-request helper';pid=$PID;maximum_hours=$MaximumHours} |
        ConvertTo-Json | Set-Content -LiteralPath (Join-Path $taskControlPath 'helper.json')
    'Automatic idle sleep inhibited; display and manual sleep unchanged.' | Add-Content -LiteralPath $taskLog
    while ([DateTime]::UtcNow -lt $taskDeadline) {
        if (Test-Path -LiteralPath (Join-Path $taskControlPath 'stop')) { break }
        Start-Sleep -Seconds 20
    }
}
finally {
    [void][AMRVACTestPower]::SetThreadExecutionState([uint32]2147483648)
    'Temporary request released; normal automatic-sleep behavior restored.' | Add-Content -LiteralPath $taskLog
}
