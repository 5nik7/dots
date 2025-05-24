source ~/catppuccin_mocha.nu

$env.config.show_banner = false

$env.config.table = {
  mode: thin
}

def --env y [...args] {
    let tmp = (mktemp -t "yazi-cwd.XXXXXX")
    yazi ...$args --cwd-file $tmp
    let cwd = (open $tmp)
    if $cwd != "" and $cwd != $env.PWD {
        cd $cwd
      }
    rm -fp $tmp
}

alias d = y

alias q = exit
alias c = clear

alias l = eza -a -l --group-directories-first --git-repos --git --icons --time-style relative --no-permissions --no-filesize --no-time --no-user --hyperlink --follow-symlinks --no-quotes
