$root = 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\MMDevices\Audio\Render'
Get-ChildItem $root -ErrorAction SilentlyContinue | ForEach-Object {
    $guid = $_.PSChildName
    $props = Get-ItemProperty (Join-Path $_.PSPath 'Properties') -ErrorAction SilentlyContinue
    $name = $props.'{a45c254e-df1c-4efd-8020-67d146a850e0},2'
    $state = (Get-ItemProperty $_.PSPath -ErrorAction SilentlyContinue).DeviceState
    $fx = Get-ItemProperty (Join-Path $_.PSPath 'FxProperties') -ErrorAction SilentlyContinue
    if ($fx) {
        $fxKeys = ($fx.PSObject.Properties | Where-Object { $_.Name -like '{*' } | ForEach-Object { "$($_.Name)=$($_.Value)" }) -join ' | '
    } else {
        $fxKeys = '(sem FxProperties)'
    }
    [pscustomobject]@{ GUID = $guid; Nome = $name; Estado = $state; FX = $fxKeys }
} | Format-List
