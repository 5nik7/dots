#!/bin/bash

awk -F '=' '/wallpaper/ {print $2}' "$HOME/.config/waypaper/config.ini" >"$HOME/.currentwallpaper" &&
	wal -i $(cat $HOME/.currentwallpaper) -n --backend $WAL_BACKEND
