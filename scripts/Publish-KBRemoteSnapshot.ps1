$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$KbDir = Join-Path $RepoRoot "ecu-kb"
$Bridge = Join-Path $KbDir "remote_bridge.py"

Push-Location $RepoRoot
try {
    python (Join-Path $RepoRoot "tools\ecu_corpus_harvester.py") init
    if ($LASTEXITCODE -ne 0) { throw "ECU corpus schema init failed" }

    python (Join-Path $RepoRoot "tools\ecu_corpus_harvester.py") seed
    if ($LASTEXITCODE -ne 0) { throw "ECU corpus seed import failed" }

    python (Join-Path $KbDir "kb.py") check
    if ($LASTEXITCODE -ne 0) { throw "kb.py check failed" }

    python $Bridge export
    if ($LASTEXITCODE -ne 0) { throw "remote snapshot export failed" }

    python $Bridge check
    if ($LASTEXITCODE -ne 0) { throw "remote snapshot verification failed" }

    git add -- "ecu-kb/remote"
    Write-Host "Verified remote specialist snapshot refreshed and staged."
    Write-Host "Review with: git diff --cached -- ecu-kb/remote"
}
finally {
    Pop-Location
}
