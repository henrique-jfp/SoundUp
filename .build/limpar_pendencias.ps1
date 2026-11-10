$ErrorActionPreference = "Stop"
$log = "C:\Projetos Pessoais\SoundUp\.build\limpar_pendencias.log"
"inicio $(Get-Date -Format o)" | Set-Content -Path $log -Encoding UTF8
$key = "HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager"
$pending = (Get-ItemProperty -Path $key -Name PendingFileRenameOperations -ErrorAction SilentlyContinue).PendingFileRenameOperations
if ($null -eq $pending) {
    "sem pendencias" | Add-Content -Path $log -Encoding UTF8
    exit 0
}
$kept = New-Object System.Collections.Generic.List[string]
$removed = 0
for ($i = 0; $i + 1 -lt $pending.Count; $i += 2) {
    $source = $pending[$i]
    $target = $pending[$i + 1]
    if ($source -match "EqualizerAPO" -or $target -match "EqualizerAPO") {
        $removed++
        "removido: $source -> $target" | Add-Content -Path $log -Encoding UTF8
    } else {
        $kept.Add($source)
        $kept.Add($target)
    }
}
if ($kept.Count -gt 0) {
    Set-ItemProperty -Path $key -Name PendingFileRenameOperations -Value ([string[]]$kept) -Type MultiString
} else {
    Remove-ItemProperty -Path $key -Name PendingFileRenameOperations -ErrorAction SilentlyContinue
}
"pares removidos: $removed; pares restantes: $($kept.Count / 2)" | Add-Content -Path $log -Encoding UTF8
"fim $(Get-Date -Format o)" | Add-Content -Path $log -Encoding UTF8
