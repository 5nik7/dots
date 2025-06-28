if cmd_exists jq; then
  location() {
    latitude="$(termux-location | jq '.["latitude"]')"
    longitude="$(termux-location | jq '.["longitude"]')"
    location="$latitude,$longitude"
    echo "$latitude,$longitude"
  }
fi

# export location="$(location)"

wttr1 () {
  curl -fGsS "wttr.in/$location?format=1" | sed 's/  //; s/+//'
}

export DROIDOTS="$DOTS/androidots"

prepend_path "$DROIDOTS/bin"

alias open="termux-open"

alias bon="export BTRY='on'"
alias boff="export BTRY=''"

alias upd="pkg update && pkg upgrade -y"

alias ".a"="cd $DROIDOTS"
alias ".af"="cd $DROIDOTS/configs"
alias ".ab"="cd $DROIDOTS/bin"

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

function pkglist(){
 pkglist="$DROIDOTS/pkglist"
  command pkg list-installed | tr '/' ' ' | awk '{print $1}' >! "$pkglist"
 sed -i '1d' "$pkglist"

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
