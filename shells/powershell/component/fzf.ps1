. "$Env:DOTCACHE\wal\wal.ps1"

$env:FZF_DEFAULT_OPTS = ''

function Set-FuzzyOpts {
  param (
    [switch]$d,
    [hashtable]$opts,
    [hashtable]$colors,
    [hashtable]$keybinds,
    [string]$previewlabel,
    [string]$borderlabel,
    [string]$inputlabel,
    [string]$listlabel,
    [string]$headerlabel
  )
  $env:FZF_DEFAULT_OPTS = ''

  $Env:FZF_FILE_OPTS = "--preview=`"bat --style=numbers --color=always {}`""
  $Env:FZF_DIRECTORY_OPTS = "--preview=`"eza -la --color=always --group-directories-first --icons --no-permissions --no-time --no-filesize --no-user --git-repos --git --follow-symlinks --no-quotes --stdin {}`""

  if ($d) {
    $Env:FZF_DEFAULT_COMMAND = 'fd --type d --strip-cwd-prefix --hidden --exclude .git'
    $previewString = $Env:FZF_DIRECTORY_OPTS
  }
  else {
    $Env:FZF_DEFAULT_COMMAND = 'fd --type f --strip-cwd-prefix --hidden --exclude .git'
    $previewString = $Env:FZF_FILE_OPTS
  }
  try {
    # Default opts
    $defaultOpts = @{
      style         = 'minimal'
      layout        = 'reverse'
      height        = '~90%'
      margin        = '1'
      border        = 'none'
      previewwindow = 'right:70%:hidden'
      prompt        = @{ symbol = '> ' }
      pointer       = @{ symbol = '' }
      marker        = @{ symbol = '┃' }
    }
    if ($opts) {
      foreach ($k in $opts.Keys) { $defaultOpts[$k] = $opts[$k] }
    }
    $opts = $defaultOpts

    # Default colors
    $defaultColors = @{
      'fg'             = $Flavor.Overlay2.Hex()
      'hl'             = ($Flavor.Subtext0.Hex() + ':underline')
      'fg+'            = ($Flavor.Teal.Hex() + ':underline:reverse')
      'hl+'            = ($Flavor.Green.Hex() + ':underline:reverse')
      'bg'             = 'transparent'
      'bg+'            = 'transparent'
      'preview-bg'     = 'transparent'
      'list-bg'        = 'transparent'
      'input-bg'       = 'transparent'
      'preview-border' = $Flavor.Surface0.Hex()
      'list-border'    = $Flavor.Surface0.Hex()
      'border'         = $Flavor.Surface0.Hex()
      'input-border'   = $Flavor.Surface1.Hex()
      'pointer'        = $Flavor.Base.Hex()
      'label'          = $Flavor.Surface2.Hex()
      'gutter'         = 'transparent'
      'marker'         = $Flavor.Yellow.Hex()
      'spinner'        = $Flavor.Surface1.Hex()
      'separator'      = $Flavor.Base.Hex()
      'query'          = $Flavor.Text.Hex()
      'info'           = $Flavor.Surface1.Hex()
      'prompt'         = $Flavor.Surface1.Hex()
      'preview-label'  = $Flavor.Surface0.Hex()
      'selected-bg'    = $Flavor.Mantle.Hex()
    }
    if ($colors) {
      foreach ($k in $colors.Keys) { $defaultColors[$k] = $colors[$k] }
    }
    $colors = $defaultColors

    # Default keybinds
    $defaultKeybinds = @{
      'ctrl-x' = 'toggle-preview'
    }
    if ($keybinds) {
      foreach ($k in $keybinds.Keys) { $defaultKeybinds[$k] = $keybinds[$k] }
    }
    $keybinds = $defaultKeybinds

    $colorString = ($colors.GetEnumerator() | ForEach-Object {
        if ($_.Value -eq 'transparent') {
          $_.Value = '-1'
        }
        "$($_.Key):$($_.Value)"
      }) -join ','
    $colorArg = "--color $colorString"

    $bindString = ($keybinds.GetEnumerator() | ForEach-Object { "$($_.Key):$($_.Value)" }) -join ','
    $keybindsArg = "--bind $bindString"

    $key_mapping = @{
      minheight     = 'min-height'
      listborder    = 'list-border'
      inputborder   = 'input-border'
      previewwindow = 'preview-window'
    }

    $optsString = ($opts.GetEnumerator() | ForEach-Object {
        $key = if ($key_mapping.ContainsKey($_.Key)) {
          $key_mapping[$_.Key]
        }
        else {
          $_.Key
        }
        if ($_.Value.enabled -eq $false) {
          '--no-{0}' -f $key
        }
        elseif ($_.Value.symbol) {
          "--{0} '{1}'" -f $key, $_.Value.symbol
        }
        else {
          '--{0} {1}' -f $key, $_.Value
        }
      }) -join ' '

    $FZF_DEFAULT_OPTS = $optsString + ' ' + $colorArg + ' ' + $keybindsArg + ' ' + $previewString
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
  }
  catch {
    Write-Host "Error: $_"
  }
}

# Example usage:
# Set-FuzzyColor 'fg+' ($Flavor.Lavender.Hex() + ':underline:reverse')
function Set-FuzzyColor {
  param (
    [Parameter(Mandatory)]
    [string]$Key,
    [Parameter(Mandatory)]
    [string]$Value
  )
  $fuzzyOpts = @{ colors = @{ $Key = $Value } }
  Set-FuzzyOpts @fuzzyOpts
}

# Example usage:
#   Set-FuzzyKeybind 'ctrl-y' 'accept'
function Set-FuzzyKeybind {
  param (
    [Parameter(Mandatory)]
    [string]$Key,
    [Parameter(Mandatory)]
    [string]$Value
  )
  $fuzzyOpts = @{ keybinds = @{ $Key = $Value } }
  Set-FuzzyOpts @fuzzyOpts
}

function Set-FuzzyOpt {
  param (
    [Parameter(Mandatory)]
    [string]$Key,
    [Parameter(Mandatory)]
    [object]$Value
  )
  $fuzzyOpts = @{ opts = @{ $Key = $Value } }
  Set-FuzzyOpts @fuzzyOpts
}

Set-FuzzyOpts

if (Test-CommandExists fzf) {
  Import-ScoopModule -Name 'PsFzf'
  Set-PsFzfOption -TabExpansion
}
