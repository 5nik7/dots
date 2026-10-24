#!/usr/bin/env zsh

export WINDOTS="$DOTS/profiles/windows"
export WINDOTFILES="$WINDOTS/config"
export WINDOWCONFIG="$WINDOTFILES"
export RAINMETER="$WINDOTS/rainmeter"


declare -xgA windot
declare -x windot[root]="${WINDOTS:-$DOTS/profiles/windows}"
declare -x windot[files]="${WINDOTFILES:-$WINDOTS/config}"
declare -x windot[configs]="${WINDOTFILES:-$WINDOTS/config}"
declare -x windot[rainmeter]="${RAINMETER:-$WINDOTS/rainmeter}"

alias ".w"="cd $windot[root]"
alias ".wc"="cd $windot[configs]"
alias ".wrm"="cd $windot[rainmeter]"

