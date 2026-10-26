# Native, builtin-only adapter; shared contract: less_style.py.
export def --env _dots-less-style [fg: string, bg: string, mode: string, enabled: string] {
    let reset = (char --unicode '001b') + '[0m'
    let marker = ($env._DOTS_LESS_STYLE? | default '')
    let owned = $marker != '' and ($env.LESS_TERMCAP_so? | default '') == $marker and ($env.LESS_TERMCAP_se? | default '') == $reset
    if (('LESS_TERMCAP_so' in $env) or ('LESS_TERMCAP_se' in $env)) and not $owned {
        hide-env --ignore-errors _DOTS_LESS_STYLE
        return
    }
    if ('LESS_TERMINFO_smso' in $env) or ('LESS_TERMINFO_rmso' in $env) {
        if $owned { hide-env --ignore-errors LESS_TERMCAP_so LESS_TERMCAP_se }
        hide-env --ignore-errors _DOTS_LESS_STYLE
        return
    }
    let color = $mode == always or ($mode == auto and ($env.TERM? | default 'dumb') != dumb and ($env.NO_COLOR? | default '') == '')
    if $nu.os-info.name == windows or $enabled != '1' or not $color {
        if $owned { hide-env --ignore-errors LESS_TERMCAP_so LESS_TERMCAP_se }
        hide-env --ignore-errors _DOTS_LESS_STYLE
        return
    }
    if $fg !~ '^#[a-fA-F0-9]{6}$' or $bg !~ '^#[a-fA-F0-9]{6}$' { return }
    let rgb = ([$fg $bg] | each {|value| [1 3 5] | each {|offset| $value | str substring $offset..($offset + 1) | into int --radix 16 } } | flatten | into string | str join ';')
    let parts = ($rgb | split row ';')
    $env.LESS_TERMCAP_so = (char --unicode '001b') + '[0;38;2;' + ($parts | first 3 | str join ';') + ';48;2;' + ($parts | last 3 | str join ';') + 'm'
    $env.LESS_TERMCAP_se = $reset
    $env._DOTS_LESS_STYLE = $env.LESS_TERMCAP_so
}
