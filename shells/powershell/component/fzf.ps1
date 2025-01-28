# if (Get-Module PSFzf -ListAvailable) {
#     Import-Module -Name PSFzf
# }
# Set-PSReadLineKeyHandler -Key Tab -ScriptBlock { Invoke-FzfTabCompletion }
# Set-PsFzfOption -TabExpansion

. "$Env:DOTCACHE\wal\wal.ps1"

$FZF_DEFAULT_COMMAND = if (Test-CommandExists fd) { 'fd --type f --strip-cwd-prefix --hidden --exclude .git' }
$env:FZF_DEFAULT_COMMAND = $FZF_DEFAULT_COMMAND


 $fzf_opts = @{
            Style                  = 'full'
            Ansi                   = $true
            Layout                 = "reverse"
            Multi                  = $true
            Height                 = '50%'
            MinHeight              = 20
            Border                 = $true
            BorderStyle            = 'sharp'
            Info                   = 'inline'
            Color                  = 'bg+:0,bg:-1,spinner:4,fg:8,header:3,info:8,pointer:13,hl:-1:underline,hl+:-1:underline:reverse,marker:14,fg+:13,prompt:8,gutter:-1,selected-bg:0,separator:$bg,preview-bg:$bg,preview-label:0,label:7,query:5,border:0,list-border:0,preview-border:0,input-border:0'
            PreviewWindow          = 'right:50%,border-sharp'
            Prompt                 = ' '
            Pointer                = '┃'
            separator              = '──'
            marker                 = '│'
            NoHScroll              = $true
        }

$_FZF_DEFAULT_OPTS = ($fzf_opts.GetEnumerator() | foreach-object { "--{0}=""{1}""" -f $_.Key, $_.Value }) -join ' '
$env:_FZF_DEFAULT_OPTS = $_FZF_DEFAULT_OPTS

$env:FZF_DEFAULT_OPTS = "--style=full --ansi --height=65% --multi --color=bg+:0,bg:-1,spinner:4 --color=fg:8,header:3,info:8,pointer:13 --color=hl:7:underline,hl+:5:reverse --color=marker:14,fg+:13,prompt:8 --color=gutter:-1,selected-bg:0,separator:0g --color=preview-bg:-1,preview-label:0,label:7,query:5 --color=border:0,list-border:0,preview-border:0,input-border:0 --info=inline --layout=reverse --prompt=' ' --pointer='┃' --separator='──' --marker='│' --scrollbar='│' --border=sharp  --preview-window=right:50%,border-sharp --preview='bat --style=numbers --color=always {}'"    