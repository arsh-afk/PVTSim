param([string]$Files)
$Files = $Files -split ','
foreach ($file in $Files) {
    Write-Output "=== $file"
    $lines = Get-Content $file
    $current = $null
    for ($i = 0; $i -lt $lines.Count; $i++) {
        $line = $lines[$i]
        if ($line -match '^- id:\s*(.+)$') { $current = $Matches[1]; $value = ''; $unit = ''; $src = '' }
        elseif ($current -and $line -match '^\s+value:\s*(.*)$') { $value = $Matches[1] }
        elseif ($current -and $line -match '^\s+unit:\s*(.*)$') { $unit = $Matches[1] }
        elseif ($current -and $line -match '^\s+source_type:\s*(.*)$') { $src = $Matches[1] }
        elseif ($current -and $line -match '^- id:') { $current = $null }
        if ($current -and $line -match '^\s+status:\s*(.*)$') {
            Write-Output ("{0} | {1} | {2} | {3} | {4}" -f $current, $value, $unit, $Matches[1], $src)
            $current = $null
        }
    }
}
