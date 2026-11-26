param([string]$GenerationDirectory)

$cache = [IO.Path]::Combine($GenerationDirectory, 'bat-cache')
$complete = [IO.File]::Exists([IO.Path]::Combine($cache, 'themes.bin')) -and
    [IO.File]::Exists([IO.Path]::Combine($cache, 'syntaxes.bin'))
if ($complete) {
    if (-not $global:DotsBatActiveCache -or $env:BAT_CACHE_PATH -ne $global:DotsBatActiveCache) {
        $global:DotsBatPreviousCache = $env:BAT_CACHE_PATH
    }
    if (-not $global:DotsBatActiveCache -or $env:BAT_THEME -cne 'Dots') {
        $global:DotsBatPreviousTheme = $env:BAT_THEME
    }
    $global:DotsBatActiveCache = $cache
    $env:BAT_THEME = 'Dots'
    $env:BAT_CACHE_PATH = $cache
} elseif ($global:DotsBatActiveCache) {
    if ($env:BAT_CACHE_PATH -eq $global:DotsBatActiveCache) { $env:BAT_CACHE_PATH = $global:DotsBatPreviousCache }
    if ($env:BAT_THEME -ceq 'Dots') { $env:BAT_THEME = $global:DotsBatPreviousTheme }
    $global:DotsBatActiveCache = $null
}
