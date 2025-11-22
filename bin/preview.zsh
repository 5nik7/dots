#!/usr/bin/env zsh

file="$(realpath "$1")"

filename="$(basename "$file")"

fext="$(echo "${filename##*.}")"
# Check if the file exists
if [[ -e "$file" ]]; then
  if [[ $(file --mime-type -b "$file") == text/* ||  $(file --mime-type -b "$file") == application/json ]]; then
      # Use highlight for syntax highlighting or fallback to cat
      (highlight -O ansi "$file" || bat --style="${BAT_STYLE:-numbers}" --color=always --pager=auto "$file") 2> /dev/null | head -500
    elif  [[ $(file --mime-type -b "$file") == */directory ]]; then
      eza -a -l --group-directories-first --git-repos --git --icons --time-style relative --no-permissions --no-filesize --no-time --no-user --hyperlink --follow-symlinks --no-quotes --color=always "$file" | head -500
    elif  [[ $(file --mime-type -b "$file") == image/* ]]; then
      chafa --size=x"$(("$LINES" / 2))" "$file"
    else
    # If not a text file, display the file type
    file "$file"
  fi
else
  # If the file does not exist, print the filename
  echo "$1"
fi

