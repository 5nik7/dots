<#
.DESCRIPTION
    Updates the desktop wallpaper.
#>
function Set-Wallpaper {
    param(
        # Path to image to set as background, if not set current wallpaper is used
        [Parameter(Mandatory = $true)][string]$image

    )

    # Trigger update of wallpaper
    # modified from https://www.joseespitia.com/2017/09/15/set-wallpaper-powershell-function/
    Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;

public class PInvoke
{
    [DllImport("User32.dll",CharSet=CharSet.Unicode)]
    public static extern int SystemParametersInfo(UInt32 action, UInt32 iParam, String sParam, UInt32 winIniFlags);
}
'@

    # Setting the wallpaper requires an absolute path, so pass image into resolve-path
    [PInvoke]::SystemParametersInfo(0x0014, 0, $($image | Resolve-Path), 0x0003) -eq 1
}

<#
.DESCRIPTION
    Gets the location of the module.
#>
function Get-ScriptDirectory {
    Split-Path $script:MyInvocation.MyCommand.Path
}

function Test-CommandExists {
    param($command)
    $exists = $null -ne (Get-Command $command -ErrorAction SilentlyContinue)
    return $exists
}

<#
.DESCRIPTION
    Copies the contents of ./templates to ~/.config/wal/templates, will clobber templates with matching names
#>
function Add-WalTemplates {
    $sourceDir = "$(Get-ScriptDirectory)/templates"
    if (!(Test-Path -Path "$HOME/.config/wal/templates")) {
        New-Item -Path "$HOME/.config/wal/templates" -ItemType Directory -ErrorAction SilentlyContinue
    }

    Get-ChildItem -Path $sourceDir | ForEach-Object {
        if (!(Test-Path -Path "$HOME/.config/wal/templates/$($_.Name)")) {
            Copy-Item -Path $_.FullName -Destination "$HOME/.config/wal/templates"
        }
    }
}

function Add-WalColorsSchemes {
    $sourceDir = "$(Get-ScriptDirectory)/colorschemes"

    if (!(Test-Path -Path "$HOME/.config/wal/colorschemes")) {
        New-Item -Path "$HOME/.config/wal/colorschemes" -ItemType Directory -ErrorAction SilentlyContinue
    }

    @('dark', 'light') | ForEach-Object {
        $schemeDir = "$sourceDir/$_"
        $configDir = "$HOME/.config/wal/colorschemes/$_"
        if (!(Test-Path -Path $schemeDir)) {
            New-Item -Path $schemeDir -ItemType Directory -ErrorAction SilentlyContinue
        }
        Get-ChildItem -Path $schemeDir | ForEach-Object {
            if (!(Test-Path -Path "$configDir/$($_.Name)")) {
                Copy-Item -Path $_.FullName -Destination "$configDir"
            }
        }
    }
}



function Update-WalCommandPrompt {
    $scriptDir = Get-ScriptDirectory
    $colorToolDir = "$scriptDir/colortool"
    $colorTool = "$colorToolDir/ColorTool.exe"
    $schemesDir = "$colorToolDir/schemes/"

    # Install color tool if needed
    if (!(Test-Path -Path $colorTool)) {
        $colorToolZip = "$scriptDir/colortool.zip"
        Invoke-WebRequest -Uri 'https://github.com/microsoft/terminal/releases/download/1904.29002/ColorTool.zip' -OutFile $colorToolZip
        Expand-Archive -Path $colorToolZip -DestinationPath $colorToolDir
        Remove-Item -Path $colorToolZip
    }

    # Make sure it was created
    $walprompt = "$HOME/.cache/wal/wal-prompt.ini"
    if (Test-Path -Path $walprompt) {
        Copy-Item -Path $walprompt -Destination "$schemesDir/wal.ini"
        & $colorTool -b wal.ini
    }
}

function Update-WalExplorer {
    $scriptDir = Get-ScriptDirectory
    $EBMDir = "$scriptDir/EBM"
    $releaseDir = "$EBMDir/Release"
    $EBMDLL = "$releaseDir/ExplorerBlurMica.dll"
    $explorerConf = "$releaseDir/config.ini"
    $rgbfile = "$HOME\.cache\wal\color0-rgb"
    $rgb_value = Get-Content -Path $rgbfile -Raw

    # Split the RGB value into individual components
    $r, $g, $b = $rgb_value -split ','

    $ini_content = @"
[config]
effect=0
clearAddress=true
clearBarBg=true
clearWinUIBg=true

[dark]
r=$r
g=$g
b=$b
a=230
"@

    if (!(Test-Path -Path $EBMDLL)) {
        $EBMZip = "$scriptDir/EBM.zip"
        Invoke-WebRequest -Uri 'https://github.com/Maplespe/ExplorerBlurMica/releases/download/2.0.1/Release_x64.zip' -OutFile $EBMZip
        Expand-Archive -Path $EBMZip -DestinationPath $EBMDir
        Remove-Item -Path $EBMZip
    }

    if (Test-Path -Path $rgbfile) {
        Set-Content -Path $explorerConf -Value $ini_content
        # taskkill /F /IM explorer.exe >nul
        # Start-Process explorer.exe
    }
}

function Update-Komorebi {

    if (!(Test-Path -Path "$HOME\.cache\wal\komorebi.json")) {
        return
    }

    $komorebiDir = "$HOME\.config\komorebi"
    $komorebiConfig = "$komorebiDir\komorebi.json"

    if (!(Test-Path -Path $komorebiConfig)) {
        return
    }

    Copy-Item -Path $komorebiConfig -Destination "$komorebiDir\komorebi.json.bak"

    $komorebiConfigData = (Get-Content -Path $komorebiConfig | ConvertFrom-Json) | Where-Object { $_ -ne $null }


    $border_colours = New-Object Collections.Generic.List[Object]

    $komorebiConfigData.border_colours | ForEach-Object { $border_colours.Add($_) }
    $komorebiWal = $(Get-Content "$HOME/.cache/wal/komorebi.json" | ConvertFrom-Json)
    $border_colours.Add($komorebiWal)

    $komorebiConfigData.border_colours = $border_colours

    $komorebiConfigData | ConvertTo-Json -Depth 32 | Set-Content -Path $komorebiConfig
}



function Update-WalTerminal {
    if (!(Test-Path -Path "$HOME/.cache/wal/windows-terminal.json")) {
        return
    }

    @(
        # Stable
        "$HOME/AppData/Local/Packages/Microsoft.WindowsTerminal_8wekyb3d8bbwe/LocalState",

        # Preview
        "$HOME/AppData/Local/Packages/Microsoft.WindowsTerminalPreview_8wekyb3d8bbwe/LocalState",

        # Stable - Scoop
        "$HOME/scoop/persist/windows-terminal/settings",

        # Preview - Scoop
        "$HOME/scoop/persist/windows-terminal-preview/settings"
    ) | ForEach-Object {
        $terminalDir = "$_"
        $terminalProfile = "$terminalDir/settings.json"

        # This version of windows terminal isn't installed
        if (!(Test-Path -Path $terminalProfile)) {
            return
        }

        Copy-Item -Path $terminalProfile -Destination "$terminalDir/settings.json.bak"

        # Load existing profile
        $configData = (Get-Content -Path $terminalProfile | ConvertFrom-Json) | Where-Object { $_ -ne $null }

        # Create a new list to store schemes
        $schemes = New-Object Collections.Generic.List[Object]

        $configData.schemes | Where-Object { $_.name -ne 'wal' } | ForEach-Object { $schemes.Add($_) }
        $walTheme = $(Get-Content "$HOME/.cache/wal/windows-terminal.json" | ConvertFrom-Json)
        $schemes.Add($walTheme)

        # Update color schemes
        $configData.schemes = $schemes

        # Set default theme as wal
        $configData.profiles.defaults | Add-Member -MemberType NoteProperty -Name colorScheme -Value 'wal' -Force

        # Set cursor to foreground color
        if ($walTheme.cursorColor) {
            $configData.profiles.defaults | Add-Member -MemberType NoteProperty -Name cursorColor -Value $walTheme.cursorColor -Force
        }
        else {
            $configData.profiles.defaults | Add-Member -MemberType NoteProperty -Name cursorColor -Value $walTheme.foreground -Force
        }

        # Write config to disk
        $configData | ConvertTo-Json -Depth 32 | Set-Content -Path $terminalProfile
    }
}

function Update-DiscordTheme {
    $discordCaschefile = "$env:DOTS\cache\wal\pywal.theme.css"
    if (!(Test-Path -Path $discordCaschefile)) {
        return
    }
    $discordTheme = "$env:APPDATA\Vencord\themes\pywal.theme.css"

    # This version of windows terminal isn't installed
    if (!(Test-Path -Path $discordTheme)) {
        return
    }
    if (Test-Path -Path "$discordTheme.bak") {
        Remove-Item -Path "$discordTheme.bak"
    }
    Copy-Item -Path $discordTheme -Destination "$discordTheme.bak"

    $(Get-Content -Path $discordCaschefile) | Set-Content -Path $discordTheme
}

function ChangeTheColors {
    # Update Discord
    Update-DiscordTheme

    # Update Windows Terminal
    Update-WalTerminal

    # Update prompt defaults
    Update-WalCommandPrompt

    # Update prompt defaults
    Update-WalExplorer

    # New oh-my-posh
    if ((Test-CommandExists oh-my-posh) -and (Test-Path -Path "$HOME/.cache/wal/posh-wal-agnoster.omp.json")) {
        if ($omp) {
            oh-my-posh init pwsh --config "$HOME/.cache/wal/posh-wal-agnoster.omp.json" | Invoke-Expression
        }
    }

    # Check if pywal fox needs to update
    if (Test-CommandExists pywalfox) {
        pywalfox update
    }

    # Terminal Icons
    if ((Get-Module -ListAvailable -Name Terminal-Icons) -and (Test-Path -Path "$HOME/.cache/wal/wal-icons.psd1")) {
        Add-TerminalIconsColorTheme -Path "$HOME/.cache/wal/wal-icons.psd1"
        Set-TerminalIconsTheme -ColorTheme wal
    }

    if ((Test-CommandExists bat) -and (Test-Path -Path "$HOME/.cache/wal/wal.tmTheme")) {
        bat cache --build
    }
}

<#
.DESCRIPTION
    Updates wal templates and themes using a new image or the existing desktop image
#>
function winwal {
    param(
        [Parameter(ParameterSetName = 'Theme', Mandatory = $true)]
        [switch]$theme,
        [Parameter(ParameterSetName = 'Theme', Position = 0)]
        [string]$themename,
        [Parameter(ParameterSetName = 'Image', Mandatory = $true)]
        [string]$image,
        [Parameter(ParameterSetName = 'Default')]
        [string]$backend = 'wal',
        [Parameter(ParameterSetName = 'Default')]
        [string]$alpha,
        [Parameter(ParameterSetName = 'Default')]
        [string]$background,
        [Parameter(ParameterSetName = 'Default')]
        [string]$foreground,
        [Parameter(ParameterSetName = 'Default')]
        [switch]$iterative,
        [Parameter(ParameterSetName = 'Default')]
        [string]$cols16,
        [Parameter(ParameterSetName = 'Default')]
        [switch]$recursive,
        [Parameter(ParameterSetName = 'Default')]
        [float]$saturate,
        [Parameter(ParameterSetName = 'Default')]
        [switch]$preview,
        [Parameter(ParameterSetName = 'Default')]
        [switch]$vte,
        [Parameter(ParameterSetName = 'Default')]
        [switch]$clearCache,
        [Parameter(ParameterSetName = 'Default')]
        [switch]$light,
        [Parameter(ParameterSetName = 'Default')]
        [switch]$noWallpaper,
        [Parameter(ParameterSetName = 'Default')]
        [string]$externalScript,
        [Parameter(ParameterSetName = 'Default')]
        [string]$saveTheme,
        [Parameter(ParameterSetName = 'Default')]
        [switch]$quiet,
        [Parameter(ParameterSetName = 'Default')]
        [switch]$restore,
        [Parameter(ParameterSetName = 'Default')]
        [switch]$skipTerminals,
        [Parameter(ParameterSetName = 'Default')]
        [switch]$skipTTY,
        [Parameter(ParameterSetName = 'Default')]
        [switch]$version,
        [Parameter(ParameterSetName = 'Default')]
        [switch]$useLastWallpaper,
        [Parameter(ParameterSetName = 'Default')]
        [switch]$skipReload,
        [Parameter(ParameterSetName = 'Default')]
        [float]$contrast,
        [Parameter(ParameterSetName = 'Default')]
        [switch]$help,
        [Parameter(ParameterSetName = 'Default')]
        [switch]$omp
    )

    Add-WalTemplates
    Add-WalColorsSchemes

    if ($help -or $PSCmdlet.MyInvocation.BoundParameters.Count -eq 0) {
        Write-Host 'Usage: winwal [-theme <theme_name>] [-image <image_path>] [-backend <backend>] [-help] [-alpha <alpha>] [-background <background>] [--fg <foreground>] [--iterative] [--cols16 <method>] [--recursive] [--saturate <0.0-1.0>] [--preview] [--vte] [-c] [-l] [-n] [-o <script_name>] [-p <theme_name>] [-q] [-R] [-s] [-t] [-v] [-w] [-e] [--contrast <1.0-21.0>]'
        Write-Host '  -theme <theme_name>  : Set the theme to use'
        Write-Host '  -image <image_path>  : Set the image to use'
        Write-Host '  -backend <backend>   : Set the backend to use'
        Write-Host '  -help                : Show this help'
        Write-Host '  -alpha <alpha>       : Set terminal background transparency'
        Write-Host '  -background <background> : Custom background color to use'
        Write-Host '  --fg <foreground>    : Custom foreground color to use'
        Write-Host '  --iterative          : Go through images in order instead of shuffled'
        Write-Host "  --cols16 <method>    : Use 16 color output 'darken' or 'lighten'"
        Write-Host '  --recursive          : Search for images recursively in subdirectories'
        Write-Host '  --saturate <0.0-1.0> : Set the color saturation'
        Write-Host '  --preview            : Print the current color palette'
        Write-Host '  --vte                : Fix text-artifacts printed in VTE terminals'
        Write-Host '  -c                   : Delete all cached colorschemes'
        Write-Host '  -l                   : Generate a light colorscheme'
        Write-Host '  -n                   : Skip setting the wallpaper'
        Write-Host "  -o <script_name>     : External script to run after 'wal'"
        Write-Host '  -p <theme_name>      : Permanently save theme with the specified name'
        Write-Host "  -q                   : Quiet mode, don't print anything"
        Write-Host '  -R                   : Restore previous colorscheme'
        Write-Host '  -s                   : Skip changing colors in terminals'
        Write-Host '  -t                   : Skip changing colors in tty'
        Write-Host "  -v                   : Print 'wal' version"
        Write-Host '  -w                   : Use last used wallpaper for color generation'
        Write-Host '  -e                   : Skip reloading gtk/xrdb/i3/sway/polybar'
        Write-Host '  --contrast <1.0-21.0>: Specify a minimum contrast ratio between palette colors and the source image'
        return
    }

    if (Get-Command 'wal' -ErrorAction SilentlyContinue) {
        if ($PSCmdlet.ParameterSetName -eq 'Theme') {
            $walCommand = 'wal --theme'
            if ($themename) {
                $walCommand += " $themename"
            }
            Invoke-Expression $walCommand
            if ($themename) {
                ChangeTheColors
            }
            return
        }

        $walCommand = "wal -n -e -s -t -i $image --backend $backend"
        if ($alpha) { $walCommand += " -a $alpha" }
        if ($background) { $walCommand += " -b $background" }
        if ($foreground) { $walCommand += " --fg $foreground" }
        if ($iterative) { $walCommand += ' --iterative' }
        if ($cols16) { $walCommand += " --cols16 $cols16" }
        if ($recursive) { $walCommand += ' --recursive' }
        if ($saturate) { $walCommand += " --saturate $saturate" }
        if ($preview) { $walCommand += ' --preview' }
        if ($vte) { $walCommand += ' --vte' }
        if ($clearCache) { $walCommand += ' -c' }
        if ($light) { $walCommand += ' -l' }
        if ($noWallpaper) { $walCommand += ' -n' }
        if ($externalScript) { $walCommand += " -o $externalScript" }
        if ($saveTheme) { $walCommand += " -p $saveTheme" }
        if ($quiet) { $walCommand += ' -q' }
        if ($restore) { $walCommand += ' -R' }
        if ($skipTerminals) { $walCommand += ' -s' }
        if ($skipTTY) { $walCommand += ' -t' }
        if ($version) { $walCommand += ' -v' }
        if ($useLastWallpaper) { $walCommand += ' -w' }
        if ($skipReload) { $walCommand += ' -e' }
        if ($contrast) { $walCommand += " --contrast $contrast" }

        # Invoke wal with the constructed command
        Invoke-Expression $walCommand

        if ($image) {
            Set-Wallpaper -Image $image
        }

        ChangeTheColors

        if ($LastExitCode -ne 0) {
            return
        }
    }
    else {
        Write-Error "Pywal not found, please install python and pywal and add it to your PATH`n`twinget install Python.Python.3.11`n`tpip install pywal"
        return
    }
}
# Return if wal failed
