#!/bin/bash

function load-wallpaper() {
	wallpaper="$(<"${HOME}/.currentwallpaper")"
	if [ -f "$wallpaper" ]; then
		swaybg -i "$wallpaper" -m fill
	fi
}

load-wallpaper
