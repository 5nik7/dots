"""Lossless binding identity with readable, non-executable display labels."""
import re

APPS = ('zsh', 'bash', 'powershell', 'tmux', 'nvim', 'yazi', 'fzf', 'kitty', 'television')
ACTIONS = {
    'backward-delete-char': 'Delete the character before the cursor',
    'vi-backward-delete-char': 'Delete backward within the current vi insertion',
    'zvm_readkeys_handler': 'Switch vi mode / read a vi key sequence',
    'vi-cmd-mode': 'Enter vi normal mode', 'vi-insert': 'Enter insert mode',
    'accept-line': 'Run the current command', 'self-insert': 'Insert the typed character',
    'fzf-history-widget': 'Search command history with FZF',
    'fzf-file-widget': 'Find and insert file paths with FZF',
    'fzf-cd-widget': 'Find a directory with FZF', 'fzf-tab-complete': 'Choose a completion with FZF',
    'backward-char': 'Move one character left', 'forward-char': 'Move one character right',
    'vi-backward-char': 'Move one character left', 'vi-forward-char': 'Move one character right',
    'history-substring-search-up': 'Find the previous matching history entry',
    'history-substring-search-down': 'Find the next matching history entry',
    'up-line-or-history': 'Move up or recall the previous command',
    'down-line-or-history': 'Move down or recall the next command',
    'zsh-system-clipboard-vicmd-vi-put-after': 'Paste from the system clipboard',
    'zsh-system-clipboard-vicmd-vi-yank-eol': 'Copy to the system clipboard through end of line',
    'select_next_entry': 'Select the next entry', 'select_prev_entry': 'Select the previous entry',
    'confirm_selection': 'Confirm the selected entry', 'quit': 'Close the application',
    'toggle_selection_down': 'Toggle selection and move down', 'toggle_selection_up': 'Toggle selection and move up',
    'toggle-preview': 'Show or hide the preview', 'accept': 'Accept the selection',
    'abort': 'Cancel the picker', 'up': 'Move to the previous result', 'down': 'Move to the next result',
    'copy-selection-and-cancel': 'Copy the selection and leave copy mode',
}
NAMES = {'esc':'Escape', 'escape':'Escape', 'enter':'Enter', 'return':'Enter', 'cr':'Enter',
         'tab':'Tab', 'btab':'Shift+Tab', 'backtab':'Shift+Tab', 'space':'Space',
         'bspace':'Backspace', 'bs':'Backspace', 'backspace':'Backspace', 'del':'Delete', 'delete':'Delete',
         'left':'Left', 'right':'Right', 'up':'Up', 'down':'Down', 'home':'Home', 'end':'End',
         'pageup':'PageUp', 'pagedown':'PageDown', 'insert':'Insert', 'leader':'Leader', 'localleader':'LocalLeader', 'double-click':'Double click', 'left-click':'Left click', 'right-click':'Right click', 'scroll-up':'Scroll up', 'scroll-down':'Scroll down'}
ANSI = {'\x1b[A':'Up', '\x1b[B':'Down', '\x1b[C':'Right', '\x1b[D':'Left',
        '\x1b[H':'Home','\x1b[F':'End','\x1b[3~':'Delete','\x1b[5~':'PageUp','\x1b[6~':'PageDown',
        '\x1b[Z':'Shift+Tab','\x1b[1;5D':'Ctrl+Left','\x1b[1;5C':'Ctrl+Right'}


def chord(value):
    value=value.strip('<>')
    parts=re.split(r'[-+]',value)
    mods=[]
    while len(parts)>1 and parts[0].lower() in ('c','ctrl','control','m','a','alt','meta','s','shift','super','d','cmd','kitty_mod'):
        mods.append({'c':'Ctrl','ctrl':'Ctrl','control':'Ctrl','m':'Alt','a':'Alt','alt':'Alt','meta':'Alt',
                     's':'Shift','shift':'Shift','super':'Super','d':'Super','cmd':'Super','kitty_mod':'KittyMod'}[parts.pop(0).lower()])
    base='-'.join(parts)
    if len(base)==1 and base.isalpha() and mods:base=base.upper()
    else:base=NAMES.get(base.lower(),base)
    return '+'.join([*mods,base])


def readable(raw):
    if isinstance(raw,list):return ' → '.join(readable(k) for k in raw)
    if not raw:return '(empty)'
    if raw.lower() in NAMES or re.fullmatch(r'(?i)(?:(?:ctrl|control|alt|meta|shift|super|kitty_mod|[cmasd])[-+])+.+',raw) or re.fullmatch(r'F\d+',raw,re.I):
        return chord(raw)
    if re.fullmatch(r'(?:Mouse|Wheel|DoubleClick|TripleClick)[A-Za-z0-9]+',raw):
        return re.sub(r'(?<=[a-z])(?=[A-Z0-9])',' ',raw)
    if raw.startswith('<'):
        return ' → '.join(chord(t) if t.startswith('<') else readable(t) for t in re.findall(r'<[^>]+>|[^<]+',raw))
    raw=re.sub(r'\\C-(.)',lambda m:chr(ord(m[1].upper())&31),raw)
    raw=raw.replace('\\M-','\x1b').replace('\\e','\x1b').replace('\\E','\x1b')
    raw=re.sub(r'\\([0-7]{3})',lambda m:chr(int(m[1],8)),raw)
    raw=re.sub(r'\\x([0-9a-fA-F]{2})',lambda m:chr(int(m[1],16)),raw)
    raw=re.sub(r'\^([@A-Z?])',lambda m:'\x7f' if m[1]=='?' else chr(ord(m[1])&31),raw)
    result=[];i=0
    while i<len(raw):
        found=next((seq for seq in sorted(ANSI,key=len,reverse=True) if raw.startswith(seq,i)),None)
        if found:result.append(ANSI[found]);i+=len(found);continue
        char=raw[i];i+=1
        if char=='\x1b':
            if i<len(raw) and raw[i].isprintable() and raw[i] not in '[O':result.append('Alt+'+raw[i].upper());i+=1
            else:result.append('Escape')
        elif char=='\x08':result.append('Ctrl+H (Backspace)')
        elif char=='\x7f':result.append('Backspace (DEL)')
        elif char=='\t':result.append('Tab')
        elif char in '\r\n':result.append('Enter')
        elif ord(char)<32:result.append('Ctrl+'+chr(ord(char)+64))
        elif char==' ':result.append('Space')
        elif char=='\\' and i<len(raw):result.append(raw[i]);i+=1
        else:result.append(char)
    return ' → '.join(result)


def record(app, mode, key, action, description='', evidence='configured', source=None, line=None, default=False, **extra):
    action=str(action)
    if re.match(r'(?i)^(?:shell(?:\s|$)|launch(?:\s|$)|<cmd>lua\s|:lua\s|!)',action):
        action=action.split()[0]+' (command omitted)'
    known=ACTIONS.get(action)
    fallback=re.sub(r'(?<=[a-z])(?=[A-Z])',' ',action)
    fallback=re.sub(r'[_-]+',' ',fallback).strip()
    # Never print function bodies or shell macro contents as descriptions.
    label=description or known or ('Action: '+fallback[:160] if fallback else 'Description unavailable')
    return dict(app=app,mode=mode,key=key,display=readable(key),action=action,description=label,
                description_source='authored' if description else 'dictionary' if known else 'identifier',
                evidence=evidence,source=str(source) if source else None,line=line,default=default,**extra)


def merge(rows):
    """Keep evidence, but identify configured rows shadowed by a live mapping."""
    def identity(r):return r['app'],r['mode'],r['display']
    live={identity(r) for r in rows if r['evidence']=='live'}
    priority=lambda r: 3 if r.get('layer')=='append_keymap' else 2 if r['default'] else 0 if r.get('layer')=='prepend_keymap' else 1
    configured={}
    for r in rows:
        if r['evidence']=='configured':configured[identity(r)]=min(configured.get(identity(r),4),priority(r))
    seen={};result=[]
    for row in rows:
        row['status']='active' if row['evidence']=='live' else 'shadowed' if identity(row) in live or priority(row)>configured.get(identity(row),4) else 'configured; activation unverified'
        exact=(*identity(row),row['evidence'],row.get('scope',''),row.get('source'),row['action'])
        if exact in seen:continue
        seen[exact]=1;result.append(row)
    return sorted(result,key=lambda r:(r['app'],r['mode'],r['display'],r['evidence']))
