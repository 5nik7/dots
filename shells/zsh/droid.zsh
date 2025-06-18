if cmd_exists jq; then
  function location() {
  latitude="$(termux-location | jq '.["latitude"]')"
  longitude="$(termux-location | jq '.["longitude"]')"
  echo "${latitude},${longitude}"
  }
fi

alias open="termux-open"

export DROIDOTS="$DOTS/androidots"

prepend_path "$DROIDOTS/bin"

alias upd="pkg update && pkg upgrade -y"

# function btry {
#   BATTERY=$(termux-battery-status | grep percentage | awk '{print $2}' | tr -d ',')
#   if (( $BATTERY >= 60 ));then
#     batcol=2
#   elif (( $BATTERY >= 30 ));then
#     batcol=3
#   else
#     batcol=1
#   fi
#   printcol "$BATTERY%\n" $batcol
# }

function google {
  termux-open-url "https://www.google.com/search?q=$*"
}

function www {
  if [[ $1 == https://* ]]; then
    termux-open-url "$1"
  else
    termux-open-url "https://$1"
  fi
}

if is_installed perl; then

  extend_path "${HOME}/perl5/bin"

  # PATH="/data/data/com.termux/files/home/perl5/bin${PATH:+:${PATH}}"; export PATH;
  PERL5LIB="${HOME}/perl5/lib/perl5${PERL5LIB:+:${PERL5LIB}}"; export PERL5LIB;
  PERL_LOCAL_LIB_ROOT="${HOME}/perl5${PERL_LOCAL_LIB_ROOT:+:${PERL_LOCAL_LIB_ROOT}}"; export PERL_LOCAL_LIB_ROOT;
  PERL_MB_OPT="--install_base \"${HOME}/perl5\""; export PERL_MB_OPT;
  PERL_MM_OPT="INSTALL_BASE=${HOME}/perl5"; export PERL_MM_OPT;
fi

prepend_path "${DOTS}/androidots/bin"
