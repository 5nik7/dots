$timeout = 1000
$pingResult = Get-CimInstance -ClassName Win32_PingStatus -Filter "Address = 'github.com' AND Timeout = $timeout" -Property StatusCode 2>$null
if ($pingResult.StatusCode -eq 0) {
    $canConnectToGitHub = $true
}
else {
    $canConnectToGitHub = $false
}

$modulePath = $PSScriptRoot

function Show-PowerNerdUsage {
    <#
    .SYNOPSIS
        Displays usage information for the PowerNerd module.
    .DESCRIPTION
        This function displays a help message with usage information for the PowerNerd module.
    .NOTES
        Author: njen
        Version: 1.0.0
    #>
    $bannerPath = Join-Path -Path $modulePath -ChildPath 'banner'
    if (Test-Path -Path $bannerPath) {
        linebreak 2
        Get-Content -Path $bannerPath | Write-Host
    }
    else {
        linebreak 2
        Write-Host -foregroundColor Yellow ' PowerNerd'
    }
    linebreak
    Write-Host -foregroundColor DarkMagenta ' NerdFont utility for PowerShell.'
    linebreak
    Write-Host ' Usage: powernerd -glyphName <name> [-code] [-list] [-install] [-help]'
    linebreak
    Write-Host -foregroundColor Yellow "`t-glyphName: " -NoNewline
    Write-Host 'The name of the glyph to retrieve.'
    Write-Host -foregroundColor Yellow "`t-code: " -NoNewline
    Write-Host 'Retrieve the glyph code instead of the character.'
    Write-Host -foregroundColor Yellow "`t-list: " -NoNewline
    Write-Host 'List all available glyphs.'
    Write-Host -foregroundColor Yellow "`t-install: " -NoNewline
    Write-Host 'Install NerdFonts.'
    Write-Host -foregroundColor Yellow "`t-help: " -NoNewline
    Write-Host 'Display this help message.'
    linebreak 2

}

# Function to fetch and parse the glyph names JSON
function Get-NerdFontGlyphs {
    <#
    .SYNOPSIS
        Fetches and parses the NerdFont glyph names JSON.
    .DESCRIPTION
        This function fetches the NerdFont glyph names JSON from the specified URL and parses it.
    .NOTES
        Author: njen
        Version: 1.0.0
    #>


    $url = 'https://raw.githubusercontent.com/ryanoasis/nerd-fonts/refs/heads/master/glyphnames.json'
    $localPath = Join-Path -Path $modulePath -ChildPath 'glyphnames.json'

    if (-not $global:canConnectToGitHub) {
        if (Test-Path -Path $localPath) {
            $localContent = Get-Content -Path $localPath -Raw
            $json = $localContent | ConvertFrom-Json
            return $json
        }
        else {
            return
        }
    }
    try {
        $localContent = Get-Content -Path $localPath -Raw
        $remoteContent = Invoke-RestMethod -Uri $url
        if ($localContent -eq $remoteContent) {
            $json = $localContent | ConvertFrom-Json
            return $json
        }
        else {
            Invoke-WebRequest -Uri $url -OutFile $localPath
            $json = $remoteContent
            return $json
        }
    }
    catch {
        Write-Err "$_"
    }
}

$nf = Get-NerdFontGlyphs

function Get-GlyphCharacter {
    <#
    .SYNOPSIS
        Retrieves the character of a specified glyph.
    .DESCRIPTION
        This function retrieves the character representation of a specified glyph from the NerdFont glyphs.
    .PARAMETER glyphName
        The name of the glyph to retrieve the character for.
    .EXAMPLE
        Get-GlyphCharacter -glyphName 'nf-fa-github'
        # This will return the character for the 'nf-fa-github' glyph.
    .NOTES
        Author: njen
        Version: 1.0.0
    #>
    param (
        [string]$glyphName
    )

    if ($nf.PSObject.Properties[$glyphName]) {
        Write-Output $nf.$glyphName.char
    }
    else {
        throw "Glyph '$glyphName' not found."
    }
}

function Get-GlyphCode {
    <#
    .SYNOPSIS
        Retrieves the code of a specified glyph.
    .DESCRIPTION
        This function retrieves the code representation of a specified glyph from the NerdFont glyphs.
    .PARAMETER glyphName
        The name of the glyph to retrieve the code for.
    .EXAMPLE
        Get-GlyphCode -glyphName 'nf-fa-github'
        # This will return the code for the 'nf-fa-github' glyph.
    .NOTES
        Author: njen
        Version: 1.0.0
    #>
    param (
        [string]$glyphName
    )

    if ($nf.PSObject.Properties[$glyphName]) {
        Write-Output $nf.$glyphName.code
    }
    else {
        throw "Glyph '$glyphName' not found."
    }
}

function Install-NerdFonts {
    <#
    .SYNOPSIS
        Installs NerdFonts.
    .DESCRIPTION
        This function installs NerdFonts by downloading and executing the installation script from the specified URL.
    .PARAMETER OptionalParameters
        Additional parameters to pass to the installation script.
    .EXAMPLE
        Install-NerdFonts
        # This will install NerdFonts using the default installation script.
    .EXAMPLE
        Install-NerdFonts -OptionalParameters @('-Font', 'FiraCode')
        # This will install the FiraCode NerdFont.
    .NOTES
        Author: njen
        Version: 1.0.0
    #>
    param (
        [Parameter(ValueFromRemainingArguments = $true)]
        $OptionalParameters
    )
    & ([scriptblock]::Create((Invoke-WebRequest 'https://to.loredo.me/Install-NerdFont.ps1').Content)) @OptionalParameters
}

function ListNerdFonts {
    $format = '{0,-4} {1}'
    $sortedGlyphs = $nf.PSObject.Properties | Sort-Object Name
    foreach ($glyph in $sortedGlyphs) {
        $glyphChar = $glyph.Value.char
        Write-Output ($format -f $glyphChar, $($glyph.Name))
    }
}

function Invoke-PowerNerd {
    <#
    .SYNOPSIS
        Main function to interact with NerdFonts.
    .DESCRIPTION
        This function provides various utilities to interact with NerdFonts, including retrieving glyph characters or codes, listing all available glyphs, and installing NerdFonts.
    .PARAMETER glyphName
        The name of the glyph to retrieve.
    .PARAMETER code
        Retrieve the glyph code instead of the character.
    .PARAMETER list
        List all available glyphs.
    .PARAMETER help
        Display the help message.
    .PARAMETER install
        Install NerdFonts.
    .EXAMPLE
        Invoke-PowerNerd -glyphName 'nf-fa-github'
        # This will return the character for the 'nf-fa-github' glyph.
    .EXAMPLE
        Invoke-PowerNerd -list
        # This will list all available glyphs.
    .EXAMPLE
        Invoke-PowerNerd -install
        # This will install NerdFonts.
    .NOTES
        Author: njen
        Version: 1.0.0
    #>
    param (
        [string]$glyphName,
        [switch]$fzf,
        [switch]$code,
        [switch]$list,
        [switch]$help,
        [switch]$install
    )


    if ($install) {
        Install-NerdFonts
        return
    }

    if ($help) {
        Show-PowerNerdUsage
        return
    }

    if ($fzf) {
        FuzzyOpts
        $env_FZF_DEFAULT_OPTS += ' ' + "--border-label=`" NERDFONT GLYPHS `" --tabstop=2 --color=16"

        $find = $args
        $selected = ListNerdFonts | Where-Object { $_ -like "*$find*" } | fzf
        if (![string]::IsNullOrWhiteSpace($selected)) { Set-Clipboard $selected }

    }

    if ($list) {
        ListNerdFonts
    }

    if ($glyphName) {
        if ($code) {
            Write-Output Get-GlyphCode -glyphName $glyphName
        }
        else {
            Write-Output Get-GlyphCharacter -glyphName $glyphName
        }
    }
}

Export-ModuleMember -Function Get-NerdFontGlyphs
Export-ModuleMember -Function Install-NerdFonts

Export-ModuleMember -Function Get-GlyphCharacter
Export-ModuleMember -Function Get-GlyphCode
Export-ModuleMember -Function Show-PowerNerdUsage
Export-ModuleMember -Function Invoke-PowerNerd
Export-ModuleMember -Function ListNerdFonts
New-Alias -Name powernerd -Scope Global -Value Invoke-PowerNerd -ErrorAction Ignore
New-Alias -Name nf -Scope Global -Value Invoke-PowerNerd -ErrorAction Ignore
