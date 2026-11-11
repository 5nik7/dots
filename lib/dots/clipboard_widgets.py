"""Explicit shell-editor integration. Generating code neither binds nor captures."""
DECODE = "import json,sys; s=sys.stdin.read(); sys.exit(1) if not s else None; d=json.loads(s); sys.stdout.buffer.write(d['text'].encode('utf-8')+b'\\0')"


def code(shell):
    if shell == 'bash':
        return '''# Evaluate explicitly in an interactive Bash session.
_dots_clipboard_widget() {
  local _dots_clip_text LC_ALL=C
  if IFS= read -r -d '' _dots_clip_text < <(dots clipboard pick --json | python3 -c 'DECODE'); then
    READLINE_LINE=${READLINE_LINE:0:READLINE_POINT}${_dots_clip_text}${READLINE_LINE:READLINE_POINT}
    READLINE_POINT=$((READLINE_POINT + ${#_dots_clip_text}))
  fi
}
bind -x '"\\C-x\\C-v":_dots_clipboard_widget'
'''.replace('DECODE',DECODE.replace("'",'"'))
    if shell == 'zsh':
        return '''# Evaluate explicitly in an interactive Zsh session.
_dots_clipboard_widget() {
  local _dots_clip_text
  if IFS= read -r -d '' _dots_clip_text < <(dots clipboard pick --json | python3 -c 'DECODE'); then
    LBUFFER+=$_dots_clip_text
  fi
  zle redisplay
}
zle -N _dots_clipboard_widget
bindkey '^X^V' _dots_clipboard_widget
'''.replace('DECODE',DECODE.replace("'",'"'))
    if shell == 'fish':
        return '''# Source explicitly in an interactive Fish session.
function _dots_clipboard_widget
  set -l _dots_clip_text
  if dots clipboard pick --json | python3 -c 'DECODE' | read --null _dots_clip_text
    commandline --insert -- "$_dots_clip_text"
  end
  commandline --function repaint
end
bind \\cx\\cv _dots_clipboard_widget
'''.replace('DECODE',DECODE.replace("'",'"'))
    if shell == 'powershell':
        return '''# Evaluate explicitly in a PowerShell session with PSReadLine.
Set-PSReadLineKeyHandler -Chord 'Ctrl+x,Ctrl+v' -BriefDescription 'Clipboard history' -ScriptBlock {
  $saved = @(& dots clipboard pick --json)
  if ($LASTEXITCODE -eq 0) {
    $entry = ConvertFrom-Json -InputObject ($saved -join [Environment]::NewLine)
    [Microsoft.PowerShell.PSConsoleReadLine]::Insert([string] $entry.text)
  }
}
'''
    raise ValueError('supported clipboard widgets: bash, zsh, fish, powershell')
