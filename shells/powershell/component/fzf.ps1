. "$Env:DOTCACHE\wal\wal.ps1"

function FuzzyOpts {
  param (
    [switch]$d,
    [string]$previewlabel,
    [string]$borderlabel,
    [string]$inputlabel,
    [string]$listlabel,
    [string]$headerlabel
  )

  $Env:FZF_FILE_OPTS = "--preview=`"bat --style=numbers --color=always {}`" --tabstop=2"
  $Env:FZF_DIRECTORY_OPTS = "--preview=`"eza -la --color=always --group-directories-first --icons --no-permissions --no-time --no-filesize --no-user --git-repos --git --follow-symlinks --no-quotes --stdin {}`" --tabstop=2"

  if ($d) {
    $Env:FZF_DEFAULT_COMMAND = 'fd --type d --strip-cwd-prefix --hidden --exclude .git'
    $previewString = $Env:FZF_DIRECTORY_OPTS
  }
  else {
    $Env:FZF_DEFAULT_COMMAND = 'fd --type f --strip-cwd-prefix --hidden --exclude .git'
    $previewString = $Env:FZF_FILE_OPTS
  }
  try {

    class FzfSymbolOpts {
      [bool]$enabled
      [string]$symbol
    }

    $fzfOptions = @{
      style         = 'full'
      padding       = 0
      margin        = 0
      ansi          = $true
      layout        = 'reverse'
      multi         = $true
      height        = '90%'
      minheight     = 20
      tabstop       = 2
      border        = 'sharp'
      listborder    = 'sharp'
      inputborder   = 'sharp'
      info          = 'inline'
      previewwindow = 'right:65%:hidden,border-sharp'
      delimiter     = ':'
      prompt        = @{ symbol = '> ' }
      pointer       = @{ symbol = '┃' }
      marker        = @{ symbol = '│' }
      separator     = [FzfSymbolOpts]@{
        enabled = $false
        symbol  = '-'
      }
      scrollbar     = [FzfSymbolOpts]@{
        enabled = $false
        symbol  = '│'
      }
    }

    $colorOptions = @{
      'fg'             = $Flavor.Overlay1.Hex()
      'hl'             = $Flavor.Overlay2.Hex() + ':underline'
      'fg+'            = $Flavor.Teal.Hex()
      'hl+'            = $Flavor.Green.Hex() + ':underline'
      'bg'             = '-1'
      'bg+'            = '-1'
      'preview-bg'     = $Flavor.Base.Hex()
      'list-bg'        = $Flavor.Base.Hex()
      'input-bg'       = $Flavor.Base.Hex()
      'preview-border' = $Flavor.Surface0.Hex()
      'list-border'    = $Flavor.Surface0.Hex()
      'border'         = $Flavor.Surface0.Hex()
      'input-border'   = $Flavor.Surface1.Hex()
      'pointer'        = $Flavor.Teal.Hex()
      'label'          = $Flavor.Surface2.Hex()
      'header'         = '8'
      'gutter'         = $Flavor.Base.Hex()
      'marker'         = '14'
      'spinner'        = '8'
      'query'          = $Flavor.Text.Hex()
      'info'           = $Flavor.Surface1.Hex()
      'prompt'         = $Flavor.Surface1.Hex()
      'preview-label'  = $Flavor.Surface0.Hex()
      'selected-bg'    = $Flavor.Mantle.Hex()
      'separator'      = $Flavor.Surface0.Hex()
    }

    $keybindsOptions = @{
      'ctrl-x' = 'toggle-preview'
    }

    $colorString = ($colorOptions.GetEnumerator() | ForEach-Object { "$($_.Key):$($_.Value)" }) -join ','
    $colorArg = "--color=$colorString"

    $bindString = ($keybindsOptions.GetEnumerator() | ForEach-Object { "$($_.Key):$($_.Value)" }) -join ','
    $keybindsArg = "--bind=$bindString"

    $key_mapping = @{
      minheight     = 'min-height'
      listborder    = 'list-border'
      inputborder   = 'input-border'
      previewwindow = 'preview-window'
    }

    $fzfString = ($fzfOptions.GetEnumerator() | ForEach-Object {
        $key = if ($key_mapping.ContainsKey($_.Key)) {
          $key_mapping[$_.Key]
        }
        else {
          $_.Key
        }
        if ($_.Value -is [bool]) {
          '--{0}' -f $key
        }
        elseif ($_.Value -is [FzfSymbolOpts] -and $_.Value.enabled -eq $false) {
          '--no-{0}' -f $key
        }
        elseif ($_.Value.symbol) {
          "--{0}='{1}'" -f $key, $_.Value.symbol
        }
        else {
          '--{0}={1}' -f $key, $_.Value
        }
      }) -join ' '

    $FZF_DEFAULT_OPTS = $fzfString + ' ' + $colorArg + ' ' + $keybindsArg + ' ' + $previewString
    if ($previewlabel) {
      $FZF_DEFAULT_OPTS += " --preview-label=' $previewlabel '"
    }
    if ($borderlabel) {
      $FZF_DEFAULT_OPTS += " --border-label=' $borderlabel '"
    }
    if ($inputlabel) {
      $FZF_DEFAULT_OPTS += " --input-label=' $inputlabel '"
    }
    if ($listlabel) {
      $FZF_DEFAULT_OPTS += " --list-label=' $listlabel '"
    }
    if ($headerlabel) {
      $FZF_DEFAULT_OPTS += " --header-label=' $headerlabel '"
    }
    $env:FZF_DEFAULT_OPTS = $FZF_DEFAULT_OPTS
    $env:_FZF_DEFAULT_OPTS = $FZF_DEFAULT_OPTS
  }
  catch {
    Write-Host "Error: $_"
  }
}

function FuzzyOptsDefaults {
  FuzzyOpts -previewlabel 'PREVIEW'
}

FuzzyOptsDefaults

function fzh {

  FuzzyOpts -borderlabel 'HISTORY'

  # Searches your command history, sets your clipboard to the selected item - Usage: fh [<string>]
  $find = $args
  $selected = Get-Content (Get-PSReadlineOption).HistorySavePath | Where-Object { $_ -like "*$find*" } | Sort-Object -Unique -Descending | fzf
  if (![string]::IsNullOrWhiteSpace($selected)) {
    Set-Clipboard $selected
  }
  FuzzyOptsDefaults
}

function fzc {

  FuzzyOpts -d -borderlabel 'CHANGE DIRECTORY'
  # Runs fzf searching files then cd's to the directory of the selected file - Usage: fzc [d | u | c]
  if ($args -eq 'd' -or $args.Count -eq 0) {
    Set-Location $Env:DOTS
  }
  elseif ($args -eq 'u') {
    Set-Location $Env:USERPROFILE
  }
  elseif ($args -eq 'c') {
    Set-Location C:\
  }
  else {
    Write-Output "Invalid argument: $args"
    return
  }
  $Host.UI.RawUI.WindowTitle = 'FZF'
  $selected = fzf
  if (![string]::IsNullOrWhiteSpace($selected)) {
    $parent = Split-Path -parent -path $selected
    Set-Location $parent
  }
  else {
    Set-Location C:\
  }
  FuzzyOptsDefaults
}

function fze {


  $env:_FZF_DEFAULT_OPTS = FuzzyOpts -f

  # Runs fzf searching files then opens the directory of the selected file in explorer - Usage: fze [d | u | c]
  if ($args -eq 'd' -or $args.Count -eq 0) {
    Set-Location $Env:DOTS
  }
  elseif ($args -eq 'u') {
    Set-Location $Env:USERPROFILE
  }
  elseif ($args -eq 'c') {
    Set-Location C:\
  }
  else {
    Write-Output "Invalid argument: $args"
    return
  }
  $Host.UI.RawUI.WindowTitle = 'FZF'
  $selected = fzf
  if (![string]::IsNullOrWhiteSpace($selected)) {
    $parent = Split-Path -parent -path $selected
    Set-Location $parent
    explorer .
  }
  else {
    Set-Location C:\
  }
}

function fzn {


  $env:_FZF_DEFAULT_OPTS = FuzzyOpts -f

  # Runs fzf searching files then opens the directory of the selected file in neovim - Usage: fzn [d | u | c]
  if ($args -eq 'd' -or $args.Count -eq 0) {
    Set-Location $Env:DOTS
  }
  elseif ($args -eq 'u') {
    Set-Location $Env:USERPROFILE
  }
  elseif ($args -eq 'c') {
    Set-Location C:\
  }
  else {
    Write-Output "Invalid argument: $args"
    return
  }
  $Host.UI.RawUI.WindowTitle = 'FZF'
  $selected = fzf
  if (![string]::IsNullOrWhiteSpace($selected)) {
    $parent = Split-Path -parent -path $selected
    Set-Location $parent
    $p = Split-Path -leaf -path (Get-Location)
    $Host.UI.RawUI.WindowTitle = "$p"
    nvim .
  }
  else {
    Set-Location C:\
  }
}

function dzc {


  $env:_FZF_DEFAULT_OPTS = FuzzyOpts -d

  # Runs fzf searching directories then cd's to the selected directory - Usage: dzc [d | u | c]
  if ($args -eq 'd' -or $args.Count -eq 0) {
    Set-Location $Env:DOTS
  }
  elseif ($args -eq 'u') {
    Set-Location $Env:USERPROFILE
  }
  elseif ($args -eq 'c') {
    Set-Location C:\
  }
  else {
    Write-Output "Invalid argument: $args"
    return
  }
  $Host.UI.RawUI.WindowTitle = 'FZF'
  $selected = fzf
  if (![string]::IsNullOrWhiteSpace($selected)) {
    Set-Location $selected
  }
  else {
    Set-Location C:\
  }
}

function dze {


  $env:_FZF_DEFAULT_OPTS = FuzzyOpts -d

  # Runs fzf searching directories then opens the selected directory in explorer - Usage: dze [d | u | c]
  if ($args -eq 'd' -or $args.Count -eq 0) {
    Set-Location $Env:DOTS
  }
  elseif ($args -eq 'u') {
    Set-Location $Env:USERPROFILE
  }
  elseif ($args -eq 'c') {
    Set-Location C:\
  }
  else {
    Write-Output "Invalid argument: $args"
    return
  }
  $Host.UI.RawUI.WindowTitle = 'FZF'
  $selected = fzf
  if (![string]::IsNullOrWhiteSpace($selected)) {
    Set-Location $selected
    explorer .
  }
  else {
    Set-Location C:\
  }
}

function dzn {


  $env:_FZF_DEFAULT_OPTS = FuzzyOpts -d

  # Runs fzf searching directories then opens the selected directory in neovim - Usage: dzn [d | u | c]
  if ($args -eq 'd' -or $args.Count -eq 0) {
    Set-Location $Env:DOTS
  }
  elseif ($args -eq 'u') {
    Set-Location $Env:USERPROFILE
  }
  elseif ($args -eq 'c') {
    Set-Location C:\
  }
  else {
    Write-Output "Invalid argument: $args"
    return
  }
  $Host.UI.RawUI.WindowTitle = 'FZF'
  $selected = fzf
  if (![string]::IsNullOrWhiteSpace($selected)) {
    Set-Location $selected
    $p = Split-Path -leaf -path (Get-Location)
    $Host.UI.RawUI.WindowTitle = "$p"
    nvim .
  }
  else {
    Set-Location C:\
  }
}

if (Test-CommandExists fzf) {
  Import-ScoopModule -Name 'PsFzf'
}
