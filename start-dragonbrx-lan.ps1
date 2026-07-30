[CmdletBinding()]
param(
    [ValidateRange(1, 65535)]
    [int]$Port = 9999,
    [ValidateRange(1, 65535)]
    [int]$DiscoveryPort = 9998
)

[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$privateRoot = Join-Path $env:USERPROFILE ".dragonbrx"
$secretFile = Join-Path $privateRoot "network.key"
$pairingFile = Join-Path $privateRoot "pairing.json"
$stateFile = Join-Path $privateRoot "distributed-state.json"
$pythonLauncher = (Get-Command py -ErrorAction Stop).Source

New-Item -ItemType Directory -Path $privateRoot -Force | Out-Null
$hasSecret = Test-Path -LiteralPath $secretFile
$hasPairing = Test-Path -LiteralPath $pairingFile
if ($hasSecret -xor $hasPairing) {
    throw (
        "Pareamento local incompleto. Preserve os arquivos existentes e " +
        "verifique $privateRoot antes de tentar novamente."
    )
}
if (-not $hasSecret) {
    Write-Host "Primeiro uso: crie uma frase-senha com pelo menos 12 caracteres."
    $firstSecure = Read-Host "Senha de pareamento" -AsSecureString
    $secondSecure = Read-Host "Repita a senha" -AsSecureString
    $firstPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR(
        $firstSecure
    )
    $secondPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR(
        $secondSecure
    )
    try {
        $firstPlain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR(
            $firstPointer
        )
        $secondPlain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR(
            $secondPointer
        )
        if ($firstPlain -cne $secondPlain) {
            throw "As senhas digitadas não coincidem."
        }
        $firstPlain | & $pythonLauncher (
            Join-Path $projectRoot "src\pairing.py"
        ) initialize `
            --pairing-file $pairingFile `
            --secret-file $secretFile `
            --password-stdin
    }
    finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($firstPointer)
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($secondPointer)
        $firstPlain = $null
        $secondPlain = $null
    }
    if ($LASTEXITCODE -ne 0) {
        throw "Não foi possível configurar a senha de pareamento."
    }
    Write-Host "Senha não armazenada; chave derivada salva fora do repositório."
}

$arguments = @(
    (Join-Path $projectRoot "src\distributed_runtime.py"),
    "central",
    "--host", "0.0.0.0",
    "--port", [string]$Port,
    "--discovery-port", [string]$DiscoveryPort,
    "--discoverable",
    "--secret-file", $secretFile,
    "--pairing-file", $pairingFile,
    "--state-file", $stateFile
)

Write-Host "Abrindo o canal DragonBRX somente na LAN."
Write-Host "No Firewall do Windows, autorize apenas redes privadas."
Push-Location $projectRoot
try {
    & $pythonLauncher @arguments
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
