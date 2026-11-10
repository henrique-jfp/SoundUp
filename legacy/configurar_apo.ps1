param(
    [ValidateRange(100, 300)]
    [int]$GainPercent = 100
)

$ErrorActionPreference = "Stop"
$apoConfig = Join-Path ${env:ProgramFiles} "EqualizerAPO\config\config.txt"
$apoConfigDir = Split-Path $apoConfig -Parent
$soundUpInclude = Join-Path $apoConfigDir "soundup-preamp.txt"

if (-not (Test-Path $apoConfig)) {
    throw "Equalizer APO não está instalado."
}

$gainDb = 20 * [Math]::Log10($GainPercent / 100.0)
$initialConfig = @"
# SoundUp preamp (managed section)
Preamp: +$($gainDb.ToString('0.00', [Globalization.CultureInfo]::InvariantCulture)) dB
PreventClipping: yes
"@
[IO.File]::WriteAllText($soundUpInclude, $initialConfig, [Text.UTF8Encoding]::new($false))
$includeLine = "Include: $soundUpInclude"
$configText = (Get-Content $apoConfig -Raw) -replace "`r`n", "`n" -replace "`r", "`n"
$configLines = $configText -split "`n" | Where-Object {
    $_ -notmatch '^\s*Include:\s*.*soundup-preamp\.txt\s*$'
}
$configText = ($configLines -join "`r`n").TrimEnd() + "`r`n$includeLine`r`n"
$backup = "$apoConfig.soundup-backup"
if (-not (Test-Path $backup)) {
    Copy-Item $apoConfig $backup
}
[IO.File]::WriteAllText($apoConfig, $configText, [Text.UTF8Encoding]::new($false))

# Allow only standard users to update SoundUp's managed file at runtime.
& icacls.exe $soundUpInclude /inheritance:r /grant '*S-1-5-32-545:M' | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Não foi possível conceder permissão para atualizar a configuração."
}

Write-Host ("SoundUp foi conectado ao Equalizer APO em {0}% (+{1:0.00} dB)." -f $GainPercent, $gainDb) -ForegroundColor Green
