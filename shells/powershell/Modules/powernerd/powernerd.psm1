

# Function to fetch and parse the glyph names JSON
function Get-NerdFontGlyphs {
    $url = "https://raw.githubusercontent.com/ryanoasis/nerd-fonts/refs/heads/master/glyphnames.json"
    $json = Invoke-RestMethod -Uri $url
    return $json
}

# Load glyphs into a variable
$nf = Get-NerdFontGlyphs

# Create a function to get the character for a given glyph name
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

function powernerd {
    param (
        [string]$glyphName,
        [switch]$list
    )
    $format = '{0,-7} {1,-5} {2}'

    if ($list) {
        $sortedGlyphs = $nf.PSObject.Properties | Sort-Object Name
        foreach ($glyph in $sortedGlyphs) {
            $char = $glyph.Value.char
            $code = $glyph.Value.code
            Write-Host ($format -f $code, $char, $($glyph.Name))
        }
    }
    else {
        return Get-GlyphCharacter -glyphName $glyphName
    }
}

# Export the functions for external use
Export-ModuleMember -Function Get-GlyphCharacter
Export-ModuleMember -Function powernerd
Export-ModuleMember -Variable nf
