param (
    [string]$folderPath
)

# Check if the folder path is provided
if (-not $folderPath) {
    Write-Host "Please provide a folder path."
    exit
}

# Get all files from the specified folder
$files = Get-ChildItem -Path $folderPath -File

# Loop through each file and run the fontforge command
foreach ($file in $files) {
    $filePath = $file.FullName
    $command = "fontforge -script font-patcher --progressbars --variable-width-glyphs --complete `"$filePath`""
    Invoke-Expression $command
}