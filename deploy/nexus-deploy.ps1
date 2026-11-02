param([switch]$Check, [switch]$NoBrowser, [switch]$Update)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Invoke-Docker([string[]]$DockerArgs) {
    & docker @DockerArgs
    if ($LASTEXITCODE -ne 0) { throw "Docker command failed (exit $LASTEXITCODE)." }
}
function New-Secret([int]$Bytes) {
    $buffer = New-Object byte[] $Bytes
    $rng = [Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($buffer) } finally { $rng.Dispose() }
    return ([BitConverter]::ToString($buffer)).Replace('-', '').ToLowerInvariant()
}
function Wait-Healthy([string]$Service, [int]$Attempts) {
    for ($i = 0; $i -lt $Attempts; $i++) {
        $cid = (Invoke-Docker ($script:ComposeArgs + @('ps', '-q', $Service)) | Out-String).Trim()
        if ($cid) {
            $state = (Invoke-Docker -DockerArgs @('inspect', '--format', '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}', $cid) | Out-String).Trim()
            if ($state -eq 'healthy') { return }
            if ($state -in @('unhealthy', 'exited', 'dead')) { throw "$Service is $state. Check Compose logs for this service." }
        }
        Start-Sleep -Seconds 2
    }
    throw "$Service did not become healthy in time."
}

$previous = Get-Location
try {
    Set-Location (Split-Path -Parent $PSScriptRoot)
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw 'Install Docker Desktop and start its Linux containers engine first.' }
    $null = Invoke-Docker -DockerArgs @('compose', 'version')
    $osType = (Invoke-Docker -DockerArgs @('info', '--format', '{{.OSType}}') | Out-String).Trim()
    if ($osType -ne 'linux') { throw 'Docker Desktop must be running with Linux containers.' }

    $envFile = Join-Path (Get-Location) '.env.nexus.local'
    if (-not (Test-Path -LiteralPath $envFile)) {
        $lines = @(
            'CAMPUSCLAW_EDITION=nexus',
            ('NEXUS_SIGNING_KEY=' + (New-Secret 32)),
            ('NEXUS_DB_PASSWORD=' + (New-Secret 24)),
            ('NEXUS_TEACHER_PASSWORD=' + (New-Secret 16)),
            ('NEXUS_STUDENT_PASSWORD=' + (New-Secret 16)),
            'NEXUS_PORT=8080', 'NEXUS_BIND_ADDRESS=127.0.0.1',
            'OPENAI_API_KEY=', 'OPENAI_BASE_URL=https://api.deepseek.com',
            'NEXUS_MODEL=deepseek-chat', 'NEXUS_SECURE_COOKIE=0', 'HF_HUB_OFFLINE=1'
        )
        # CreateNew prevents overwriting a configuration created concurrently.
        $stream = [IO.File]::Open($envFile, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
        try {
            $bytes = [Text.Encoding]::UTF8.GetBytes(($lines -join "`n") + "`n")
            $stream.Write($bytes, 0, $bytes.Length)
        } finally { $stream.Dispose() }
        Write-Host 'Created .env.nexus.local with random credentials. Keep it private.'
    }
    if (-not (Test-Path -LiteralPath $envFile -PathType Leaf) -or (Get-Item -LiteralPath $envFile).Length -eq 0) { throw 'The local environment file must be a nonempty regular file.' }
    $script:ComposeArgs = @('compose', '--env-file', $envFile, '-f', 'docker-compose.nexus.yml')
    $null = Invoke-Docker ($script:ComposeArgs + @('config', '--quiet'))
    $port = 8080
    foreach ($line in Get-Content -LiteralPath $envFile) {
        if ($line -match '^NEXUS_PORT=(.*)$') {
            if (-not [int]::TryParse($Matches[1].Trim(), [ref]$port) -or $port -lt 1 -or $port -gt 65535) { throw 'NEXUS_PORT must be between 1 and 65535.' }
        }
    }
    $cid = (Invoke-Docker ($script:ComposeArgs + @('ps', '-q', 'api')) | Out-String).Trim()
    if (-not $cid) {
        $listener = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback, $port)
        try { $listener.Start() } catch { throw "Port $port is occupied. Change NEXUS_PORT in .env.nexus.local." } finally { $listener.Stop() }
    }
    if ($Check) { Write-Host 'PASS: Docker, Linux engine, Compose configuration and port preflight.'; exit 0 }

    # Daily startup reuses the image. Rebuild only on first install or explicit update.
    $imageExists = [bool](Invoke-Docker -DockerArgs @('image', 'ls', '--quiet', 'campusclaw-nexus-group:local') | Out-String).Trim()
    if ($Update -or -not $imageExists) {
        Invoke-Docker ($script:ComposeArgs + @('build', 'api'))
    }
    Invoke-Docker ($script:ComposeArgs + @('up', '-d', '--no-build', '--no-recreate', 'db', 'redis'))
    Wait-Healthy 'db' 60
    Wait-Healthy 'redis' 30
    # Use database state rather than a local marker (which can be lost on a new clone).
    $hasUsersTable = (Invoke-Docker ($script:ComposeArgs + @('exec', '-T', 'db', 'psql', '-U', 'nexus', '-d', 'nexus', '-Atc', "SELECT to_regclass('public.users') IS NOT NULL")) | Out-String).Trim()
    if ($hasUsersTable -notin @('t', 'f')) { throw 'Could not determine database initialization state.' }
    $initialized = $false
    if ($hasUsersTable -eq 't') {
        $hasUsers = (Invoke-Docker ($script:ComposeArgs + @('exec', '-T', 'db', 'psql', '-U', 'nexus', '-d', 'nexus', '-Atc', 'SELECT EXISTS (SELECT 1 FROM users LIMIT 1)')) | Out-String).Trim()
        if ($hasUsers -notin @('t', 'f')) { throw 'Could not determine account initialization state.' }
        $initialized = $hasUsers -eq 't'
    }
    if (-not $initialized) {
        Write-Host 'First installation: initializing the empty database.'
        Invoke-Docker ($script:ComposeArgs + @('run', '--rm', '--no-deps', 'api', 'python', 'scripts/nexus_init.py'))
    } elseif ($Update) {
        Invoke-Docker ($script:ComposeArgs + @('stop', 'api', 'worker', 'scheduler'))
        Invoke-Docker ($script:ComposeArgs + @('run', '--rm', '--no-deps', 'api', 'python', 'scripts/nexus_init.py', '--migrate-only'))
    } else {
        Write-Host 'Existing database retained. Skipping migration and seed initialization.'
    }
    if ($Update) {
        Invoke-Docker ($script:ComposeArgs + @('up', '-d', '--no-build', '--force-recreate', 'api', 'worker', 'scheduler'))
    } else {
        Invoke-Docker ($script:ComposeArgs + @('up', '-d', '--no-build', '--no-recreate', 'api', 'worker', 'scheduler'))
    }
    Wait-Healthy 'api' 90
    Invoke-Docker ($script:ComposeArgs + @('ps'))
    $url = "http://127.0.0.1:$port/"
    Write-Host "PASS: Nexus is healthy at $url"
    Write-Host 'Demo users: teacher_a, student_a1, student_b1. Passwords are in .env.nexus.local.'
    if (-not $NoBrowser) { Start-Process $url }
    exit 0
} catch {
    [Console]::Error.WriteLine('ERROR: ' + $_.Exception.Message)
    exit 1
} finally {
    Set-Location $previous
}
