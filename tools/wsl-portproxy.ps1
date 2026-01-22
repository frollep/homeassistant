param(
    [int[]]$Ports = @(8123, 3000, 8086),
    [string]$Distro = "Ubuntu-22.04",
    [string]$ProjectDir = "/mnt/c/Users/hojta/source/repos/homeassistant",
    [int]$WaitSeconds = 180
)

$ErrorActionPreference = "Stop"

function Get-WslIp {
    $ipRaw = (wsl.exe -d $Distro -e sh -c "hostname -I").Trim()
    if ([string]::IsNullOrWhiteSpace($ipRaw)) {
        return $null
    }
    return ($ipRaw -split "\s+")[0]
}

function Wait-ForWsl {
    $start = Get-Date
    while ($true) {
        $ip = Get-WslIp
        if ($ip) {
            return $ip
        }
        if ((Get-Date) - $start -gt (New-TimeSpan -Seconds $WaitSeconds)) {
            throw "Timed out waiting for WSL to report an IP."
        }
        Start-Sleep -Seconds 2
    }
}

function Ensure-Containers {
    wsl.exe -d $Distro -e sh -lc "cd '$ProjectDir' && docker compose up -d" | Out-Null
}

function Wait-ForContainers {
    $start = Get-Date
    while ($true) {
        $status = wsl.exe -d $Distro -e sh -lc "cd '$ProjectDir' && docker compose ps --status running --format '{{.Name}}'"
        $names = ($status -split "`r?`n") | Where-Object { $_ -and $_.Trim() -ne "" }
        if ($names.Count -ge 3) {
            return
        }
        if ((Get-Date) - $start -gt (New-TimeSpan -Seconds $WaitSeconds)) {
            throw "Timed out waiting for containers to be running."
        }
        Start-Sleep -Seconds 3
    }
}

$wslIp = Wait-ForWsl
Write-Host "WSL IP: $wslIp"

Ensure-Containers
Wait-ForContainers

foreach ($port in $Ports) {
    & netsh interface portproxy delete v4tov4 listenaddress=0.0.0.0 listenport=$port | Out-Null
    & netsh interface portproxy add v4tov4 listenaddress=0.0.0.0 listenport=$port connectaddress=$wslIp connectport=$port | Out-Null

    $ruleName = "WSL Portproxy $port"
    & netsh advfirewall firewall delete rule name="$ruleName" | Out-Null
    & netsh advfirewall firewall add rule name="$ruleName" dir=in action=allow protocol=TCP localport=$port | Out-Null

    Write-Host "Updated port $port -> ${wslIp}:$port"
}
