#!/usr/bin/env zah

export DROIDOTS="$DOTS/profiles/termux"
export DOTERMUX="$DROIDOTS/termux"
export DROIDBIN="$DROIDOTS/bin"
export DROIDCONFIGS="$DROIDOTS/config"
export DROIDSHELLS="$DROIDOTS/shells"
export DROIDZSH="$DROIDSHELLS/zsh"

declare -xgA droid
declare -x droid[termux]="$DROIDOTS/termux"
declare -x droid[root]="$DOTS/profiles/termux"
declare -x droid[bin]="$DROIDOTS/bin"
declare -x droid[configs]="$DROIDOTS/config"
declare -x droid[shells]="$DROIDOTS/shells"
declare -x droid[zsh]="$DROIDSHELLS/zsh"
declare -x zsh[local]="$HOME/.zshrc.local"

alias ".a"="cd $droid[root]"
alias ".ac"="cd $droid[configs]"
alias ".ab"="cd $droid[bin]"
alias ".as"="cd $droid[shells]"
alias ".asz"="cd $droid[zsh]"
alias ".v"="cd ${droid[configs]}/nvim"
