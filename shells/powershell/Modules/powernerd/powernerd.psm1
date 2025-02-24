$modulePath = $PSScriptRoot


function Show-PowerNerdUsage {
    $bannerPath = Join-Path -Path $modulePath -ChildPath "banner"
    if (Test-Path -Path $bannerPath) {
        Write-Host " "
        Get-Content -Path $bannerPath | Write-Host
    }
    else {
        Write-Host " "
        Write-Host -foregroundColor Yellow "PowerNerd"
    }
    Write-Host " "
    Write-Host -foregroundColor DarkGray " NerdFont utility for PowerShell."
    Write-Host " "
    Write-Host " powernerd -glyphName <name> [-code] [-list] [-help]"
    Write-Host " "
    Write-Host -foregroundColor Yellow "`t-glyphName: " -NoNewline
    Write-Host "The name of the glyph to retrieve."
    Write-Host -foregroundColor Yellow "`t-code: " -NoNewline
    Write-Host "Retrieve the glyph code instead of the character."
    Write-Host -foregroundColor Yellow "`t-list: " -NoNewline
    Write-Host "List all available glyphs."
    Write-Host -foregroundColor Yellow "`t-help: " -NoNewline
    Write-Host "Display this help message."
    Write-Host " "

}

# Function to fetch and parse the glyph names JSON
function Get-NerdFontGlyphs {
    $url = "https://raw.githubusercontent.com/ryanoasis/nerd-fonts/refs/heads/master/glyphnames.json"
    $localPath = Join-Path -Path $modulePath -ChildPath "glyphnames.json"

    if (Test-Path -Path $localPath) {
        $localContent = Get-Content -Path $localPath -Raw
        $remoteContent = Invoke-RestMethod -Uri $url

        if ($localContent -eq $remoteContent) {
            $localjson = $localContent | ConvertFrom-Json
            return $localjson
        }
        else {
            Invoke-WebRequest -Uri $url -OutFile $localPath
            $json = $remoteContent
            return $json
        }
    }
    else {
        Invoke-WebRequest -Uri $url -OutFile $localPath
        $json = Invoke-RestMethod -Uri $url
        return $json
    }
}

$nf = Get-NerdFontGlyphs

function Get-GlyphCharacter {
    param (
        [string]$glyphName
    )

    if ($nf.PSObject.Properties[$glyphName]) {
        return $nf.$glyphName.char
    }
    else {
        throw "Glyph '$glyphName' not found."
    }
}

function Get-GlyphCode {
    param (
        [string]$glyphName
    )

    if ($nf.PSObject.Properties[$glyphName]) {
        return $nf.$glyphName.code
    }
    else {
        throw "Glyph '$glyphName' not found."
    }
}

function Invoke-PowerNerd {
    param (
        [string]$glyphName,
        [switch]$code,
        [switch]$list,
        [switch]$help
    )
    $format = '{0,-7} {1,-5} {2}'

    if ($help) {
        Show-PowerNerdUsage
    }

    if ($list) {
        $sortedGlyphs = $nf.PSObject.Properties | Sort-Object Name
        foreach ($glyph in $sortedGlyphs) {
            $glyphChar = $glyph.Value.char
            $glyphCode = $glyph.Value.code
            Write-Host ($format -f $glyphCode, $glyphChar, $($glyph.Name))
        }
    }
    if ($glyphName) {
        if ($code) {
            return Get-GlyphCode -glyphName $glyphName
        }
        else {
            return Get-GlyphCharacter -glyphName $glyphName
        }
    }
    else {
        Show-PowerNerdUsage
    }
}

function nf ($glyphName) {
    if ($nf.PSObject.Properties[$glyphName]) {
        return $nf.$glyphName.char
    }
    else {
        throw "Glyph '$glyphName' not found."
    }
}


Export-ModuleMember -Function Get-GlyphCharacter
Export-ModuleMember -Function Get-GlyphCode
Export-ModuleMember -Function Show-PowerNerdUsage
Export-ModuleMember -Function Invoke-PowerNerd
Export-ModuleMember -Function ng
New-Alias -Name powernerd -Scope Global -Value Invoke-PowerNerd -ErrorAction Ignore
Export-ModuleMember -Variable nf
