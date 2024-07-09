<#
    .DESCRIPTION

    .PARAMETER t
        Sets the theme.
    .PARAMETER i
        Pywal integration.
    .EXAMPLE
        drip -t "Theme"
    .EXAMPLE
        drip -i "Image" -be "colorz" -Sat "0.5"
    .NOTES
        Supports jpg, png and bmp files.
    #>

param(
  [string]$t,
  [string]$i,
  [string]$Sat,
  [string]$be
)
$ENV:DRIP = "$ENV:DOTS\drip"
$ENV:WALLS = "$ENV:DOTS\walls"
if ($t) {
  $wall = $(Get-Content "$ENV:DRIP\$t\wall")
  $wp = "$ENV:WALLS\$wall"
  wal --theme "$t" -n
  Set-Wall -PicturePath "$wp" -Style Fill
  $ENV:THEME = $t
}
if ($i) {
  if ($be) {
    $colorpicker = $be
  }
  elseif ($ENV:WALBACKEND) {
    $colorpicker = $ENV:WALBACKEND
  }
  else {
    $colorpicker = "wal"
  }
  if ($Sat) {
    wal -n -i $i --backend $colorpicker --saturate $Sat
  }
  else {
    wal -i "$i" -n --backend $colorpicker
  }
  Set-Wall -PicturePath "$i" -Style Fill
}