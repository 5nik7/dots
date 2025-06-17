
THEME=$(echo "$DOT_THEME" | cut -d '-' -f 1)
if [ $THEME = 'catppuccin' ]; then
  FLAVOR=$(echo "$DOT_THEME" | cut -d '-' -f 2)
  export "$FLAVOR"
fi

if cmd_exists catppuccin; then
  mocha() {
    catppuccin mocha "$@"
  }
  flavor() {
    catppuccin "$FLAVOR" "$@"
  }
fi
