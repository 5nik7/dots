#!/bin/bash

wallpaper="$(<"${HOME}/.currentwallpaper")"
if [ -f "$wallpaper" ]; then
	swaybg -i "$wallpaper" -m fill
fi
