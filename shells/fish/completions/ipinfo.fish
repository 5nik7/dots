function __complete_ipinfo
    set -lx COMP_LINE (commandline -cp)
    test -z (commandline -ct)
    and set COMP_LINE "$COMP_LINE "
    /data/data/com.termux/files/home/go/bin/ipinfo
end
complete -f -c ipinfo -a "(__complete_ipinfo)"
