#$dir1 = "C:\Users\njen\dots\shells\powershell\Modules"
#$dir2 = "C:\Users\njen\Documents\WindowsPowerShell\Modules"

param(
      [string]$Path1,
      [string]$Path2
)


$dir1 = $Path1
$dir2 = $Path2

function RepeatString {
    param(
        [string]$Text,
        [int]$Count
    )

    if ($Count -le 0 -or $null -eq $Text) {
        return ''
    }

    $Text * $Count
}

function FileCount {
  param (
    [string]$Directory
  )
  (Get-ChildItem "$Directory" -File -Recurse | Measure-Object).Count
}

$dir1Count = FileCount $dir1
$dir2Count = FileCount $dir2
$CountOut1 = "'$dir1' = '$dir1Count'"
$CountOut2 = "'$dir2' = '$dir2Count'"
$maxCountLength = [Math]::Max($CountOut1.Length, $CountOut2.Length)
function separator {
  $Count = $maxCountLength
  $Text = '─'
  RepeatString $Text $Count
}

Write-Host
Write-Host "Comparing:"

Write-Host "┌󰎦'$dir1'"
Write-Host "└󰎩'$dir2'"
Write-Host
Write-Host "File Count:"
Write-Host (separator)
Write-Host "'$dir1' = '$dir1Count'"
Write-Host "'$dir2' = '$dir2Count'"
Write-Host (separator)
function test1 {
  Write-Host
  Write-Host "TEST1:"
  Write-Host

  $files1 = Get-ChildItem $dir1 -File -Recurse

  Write-Host "Only in '$dir1'"

  foreach ($file1 in $files1) {
    $relative = $file1.FullName.Substring($dir1.Length).TrimStart('\')
    $file2 = Join-Path $dir2 $relative

    if (-not (Test-Path $file2)) {
      Write-Host " - $relative"
      continue
    }

    $hash1 = (Get-FileHash $file1.FullName).Hash
    $hash2 = (Get-FileHash $file2).Hash

    if ($hash1 -ne $hash2) {
      Write-Host "Different: $relative"
    }
  }

  Write-Host

  Write-Host "Only in '$dir2'"
  Get-ChildItem $dir2 -File -Recurse | ForEach-Object {
    $relative = $_.FullName.Substring($dir2.Length).TrimStart('\')
    $file1 = Join-Path $dir1 $relative

    if (-not (Test-Path $file1)) {
      Write-Host " - $relative"
    }
  }
}

function test2 {
  Write-Host
  Write-Host
  Write-Host "TEST2:"

  $f1 = Get-ChildItem $dir1 -File -Recurse | ForEach-Object {
    $_.FullName.Substring($dir1.Length).TrimStart('\')
  }

  $f2 = Get-ChildItem $dir2 -File -Recurse | ForEach-Object {
    $_.FullName.Substring($dir2.Length).TrimStart('\')
  }

  Compare-Object $f1 $f2
}

test1
test2
