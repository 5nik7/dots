if has catppuccin; then

  export rosewater=$(catppuccin rosewater)
  export flamingo=$(catppuccin flamingo)
  export pink=$(catppuccin pink)
  export mauve=$(catppuccin mauve)
  export red=$(catppuccin red)
  export maroon=$(catppuccin maroon)
  export peach=$(catppuccin peach)
  export yellow=$(catppuccin yellow)
  export green=$(catppuccin green)
  export teal=$(catppuccin teal)
  export sky=$(catppuccin sky)
  export sapphire=$(catppuccin sapphire)
  export blue=$(catppuccin blue)
  export lavender=$(catppuccin lavender)
  export text=$(catppuccin text)
  export subtext1=$(catppuccin subtext1)
  export subtext0=$(catppuccin subtext0)
  export overlay2=$(catppuccin overlay2)
  export overlay1=$(catppuccin overlay1)
  export overlay0=$(catppuccin overlay0)
  export surface2=$(catppuccin surface2)
  export surface1=$(catppuccin surface1)
  export surface0=$(catppuccin surface0)
  export base=$(catppuccin base)
  export mantle=$(catppuccin mantle)
  export crust=$(catppuccin crust)

else
  echo "catppuccin command not found. Please install it to use the colors."
fi
