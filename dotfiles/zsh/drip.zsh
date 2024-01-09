export DRIP="$(< "${HOME}/.drip")"

export THEME="$DOTS/themes/$DRIP"

if [ ! -e "$THEME" ]; then
    ln -sf $THEME $HOME/.theme
fi

# BASE16_SHELL="$HOME/.config/base16-shell/"
# [ -n "$PS1" ] && \
#     [ -s "$BASE16_SHELL/profile_helper.sh" ] && \
#         source "$BASE16_SHELL/profile_helper.sh"

# source_path "$HOME/.cache/wal/colors.sh"
