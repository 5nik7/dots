"""Picker presentation and disposable preview-session wiring; no mutations."""
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile


def preview_command(root):
    args = [sys.executable, '-I', str(Path(__file__).with_name('preview.py')), str(root)]
    if os.name == 'nt':
        # A fixed PowerShell invocation, never cmd.exe interpolation of paths.
        shell = os.environ.get('BLASTOFF_NATIVE_PWSH') or shutil.which('pwsh')
        if not shell:
            raise RuntimeError('Native PowerShell 7+ is required for Windows previews; invoke Blastoff from its PowerShell module')
        command = '& ' + ' '.join("'"+arg.replace("'", "''")+"'" for arg in args) + ' {1}'
        return subprocess.list2cmdline([shell, '-NoProfile', '-NonInteractive', '-Command']), command
    shell = shutil.which('sh') or shutil.which('bash')
    if not shell:
        # Termux test/launcher environments can intentionally omit PATH tools.
        for candidate in (Path(sys.executable).parent/'sh', Path('/bin/sh')):
            if candidate.is_file():
                shell = str(candidate); break
    return (shlex.join([shell, '-c']), shlex.join(args)+' {1}') if shell else (None,None)


# Only nonexecuting options with understood arity reach the child.
VALUES = {'--layout','--height','--min-height','--margin','--padding','--border','--color',
          '--info','--pointer','--marker','--separator','--scrollbar','--tabstop',
          '--style','--border-label','--border-label-pos','--list-border','--input-border','--header-border',
          '--hscroll-off','--scroll-off','--scheme','--algo','--tiebreak'}
FLAGS = {'--cycle','--no-cycle','--no-mouse','--mouse','--no-bold','--bold','--no-unicode',
         '--unicode','--hscroll','--no-hscroll','--exact','--no-exact','--extended',
         '--no-extended','--ignore-case','--no-ignore-case','--smart-case','--literal',
         '--no-literal','--no-sort','--sort','--tac','--no-tac','--reverse'}
ACTIONS = {'up','down','page-up','page-down','half-page-up','half-page-down','first','last',
           'backward-char','forward-char','backward-word','forward-word','beginning-of-line',
           'end-of-line','backward-delete-char','delete-char','backward-kill-word',
           'kill-word','kill-line','unix-line-discard','clear-query','toggle-sort'}
RESERVED = {'enter','esc','ctrl-c','ctrl-x','tab','shift-tab'}


def safe_binding(value):
    import re
    for binding in value.split(','):
        if ':' not in binding:
            return False
        key, actions = binding.split(':',1)
        if key in RESERVED or not re.fullmatch(r'(?:ctrl-|alt-|shift-)?(?:[a-z0-9]|up|down|left|right|pgup|pgdn|home|end)', key):
            return False
        if not set(actions.split('+')) <= ACTIONS:
            return False
    return bool(value)


def option_words(source):
    """fzf shell words: comments start at a word boundary, not inside hex colors.

    No variable, command or backtick expansion. shlex handles quotes/escapes
    after this narrow comment pass (its built-in comments eat embedded '#').
    """
    output = []; quote = None; escaped = False; boundary = True; comment = False
    for char in source:
        if comment:
            if char == '\n': comment = False; output.append(char); boundary = True
            continue
        if escaped:
            output.append(char); escaped = False; boundary = False; continue
        if char == '\\' and quote != "'":
            output.append(char); escaped = True; boundary = False; continue
        if quote:
            output.append(char)
            if char == quote: quote = None
            continue
        if char in ("'", '"'):
            quote = char; output.append(char); boundary = False
        elif char == '#' and boundary:
            comment = True
        else:
            output.append(char); boundary = char.isspace()
    return shlex.split(''.join(output), comments=False)


def inherited_options(env, diagnostic=None):
    import stat
    values, omitted = [], []
    sources = []
    if env.get('FZF_DEFAULT_OPTS_FILE'):
        try:
            path = Path(env['FZF_DEFAULT_OPTS_FILE']).expanduser()
            fd = os.open(path, os.O_RDONLY | getattr(os,'O_NONBLOCK',0))
            with os.fdopen(fd,'rb') as file:
                if not stat.S_ISREG(os.fstat(file.fileno()).st_mode):
                    raise ValueError('not a regular options file')
                content = file.read(65537)
            if len(content)>65536: raise ValueError('options exceed 64 KiB')
            sources.append(('FZF_DEFAULT_OPTS_FILE', content.decode('utf-8')))
        except (OSError,ValueError) as e:
            omitted.append('FZF_DEFAULT_OPTS_FILE: '+str(e))
    sources.append(('FZF_DEFAULT_OPTS', env.get('FZF_DEFAULT_OPTS','')))
    for label, source in sources:
        try:
            if len(source)>65536: raise ValueError('options exceed 64 KiB')
            words = option_words(source)
        except ValueError as e:
            omitted.append(label+': '+str(e)); continue
        i=0
        while i<len(words):
            word=words[i]; word={'-e':'--exact','-i':'--ignore-case','+i':'--no-ignore-case'}.get(word,word)
            flag,sep,value=word.partition('='); i+=1
            if flag in FLAGS and not sep:
                values.append(flag)
            elif flag in VALUES or flag=='--bind':
                if not sep:
                    # fzf optional-value forms are accepted without consuming a flag.
                    if i<len(words) and (not words[i].startswith('-') or (len(words[i])>1 and words[i][1].isdigit())):
                        value=words[i]; i+=1
                    elif flag in ('--border','--info','--separator','--scrollbar'):
                        value={'--border':'rounded','--info':'default','--separator':'─','--scrollbar':'│'}[flag]
                    else:
                        omitted.append(flag); continue
                if flag=='--bind':
                    bindings = value.split(',')
                    kept = [binding for binding in bindings if safe_binding(binding)]
                    if len(kept) != len(bindings): omitted.append('--bind (reserved/executing action)')
                    if not kept: continue
                    value = ','.join(kept)
                # All display strings are untrusted; never replay terminal controls.
                if any(not c.isprintable() for c in value):
                    omitted.append(flag); continue
                values.append(flag+'='+value)
            else:
                omitted.append(flag)
                if not sep and i<len(words) and not words[i].startswith('-'): i+=1
    if omitted and diagnostic:
        diagnostic('Incompatible/unreadable fzf settings ignored; use --verbose for details','warning')
        diagnostic('Ignored fzf options: '+', '.join(omitted))
    return values


def fzf_args(width, height, color, shell, command, *, fancy=None, multi=False, kind='local', inherited=()):
    args = ['fzf', *inherited]
    if fancy:
        args += ['--height=90%', '--layout=reverse', '--border=sharp', '--border-label= BLASTOFF ']
        unicode_ok = fancy != 'ascii' and 'utf' in (sys.stdout.encoding or '').lower() and os.environ.get('TERM') != 'dumb'
        args += ['--unicode' if unicode_ok else '--no-unicode']
        if color:
            args += ['--color=fg:#e6dcfa,bg:-1,hl:#ff43bf,fg+:#ffffff,bg+:#34204d,hl+:#ff43bf,border:#8955ff,prompt:#ff43bf,pointer:#ff43bf,header:#b08aff']
    if not color:
        args += ['--color=bw','--no-bold']
    action = 'delete selection' if multi else 'show' if kind=='module' else 'apply'
    args += ['--prompt='+('Backup' if multi else 'Module' if kind=='module' else 'Theme')+' > ',
             '--delimiter=\t','--with-nth=2..', '--multi' if multi else '--no-multi',
             '--bind=enter:accept,esc:abort,ctrl-c:abort',
             '--header=Enter '+action+' | Esc/Ctrl-C cancel'+(' | Tab/Shift-Tab select' if multi else '')+' | Ctrl-X preview']
    if multi: args += ['--bind=tab:toggle+down,shift-tab:toggle+up']
    if command:
        args += ['--with-shell='+shell,'--preview='+command,
                 '--preview-window=right,60%,border-left,wrap,<60(down,45%,border-top,wrap)',
                 '--bind=ctrl-x:toggle-preview']
    return args


def choose_fzf(values, themes, color, env, *, fancy=None, multi=False, kind='local', labels=None, diagnostic=None, executable=None):
    size=shutil.get_terminal_size((80,24))
    resolved_tools={'fzf':executable or shutil.which('fzf'), 'bat':shutil.which('bat'),
                    'starship':shutil.which('starship') if any(value.startswith('preset:') for value in values) else None}
    if diagnostic:
        diagnostic('Picker presentation: '+('fancy '+fancy if fancy else 'basic fzf')+'; color: '+str(color))
        diagnostic('fzf options: file='+str(env.get('FZF_DEFAULT_OPTS_FILE') or '(unset)')+
                   '; environment='+('set' if env.get('FZF_DEFAULT_OPTS') else 'unset')+
                   '; shell aliases/functions are not inherited')
        # Probe only for verbose sessions, once per browser, never per preview.
        if getattr(getattr(diagnostic, '__self__', None), 'args', None) is not None and diagnostic.__self__.args.verbose:
            for executable, options in [('fzf',['--version']),('bat',['--config-file']),('bat',['--cache-dir'])]:
                resolved=resolved_tools[executable]
                if resolved:
                    try:
                        diagnostic(executable+' executable: '+resolved)
                        probe=subprocess.run([resolved,*options],capture_output=True,text=True,env=env,timeout=2)
                        diagnostic(executable+' '+options[0]+': '+probe.stdout.strip()[:1024])
                    except (OSError,UnicodeError,subprocess.TimeoutExpired): diagnostic(executable+' configuration probe unavailable')
            for key in ('BAT_THEME','BAT_CONFIG_PATH','BAT_CONFIG_DIR','BAT_CACHE_PATH','NO_COLOR'):
                if key in env: diagnostic(key+'='+env[key])
    inherited=inherited_options(env,diagnostic)
    labels=labels or values
    with tempfile.TemporaryDirectory(prefix='blastoff-preview-') as tmp:
        root=Path(tmp)
        doc={'choices':values,'themes':str(themes),'color':color,
             'starship':resolved_tools['starship'],'bat':resolved_tools['bat']}
        (root/'choices.json').write_text(json.dumps(doc),encoding='utf-8')
        shell,command=preview_command(root)
        child_env={k:v for k,v in env.items() if not k.startswith('GUM_') and k not in ('FZF_DEFAULT_OPTS','FZF_DEFAULT_OPTS_FILE','FZF_DEFAULT_COMMAND','BASH_ENV','ENV','ZDOTDIR')}
        arguments=fzf_args(size.columns,size.lines,color,shell,command,fancy=fancy,multi=multi,kind=kind,inherited=inherited)
        arguments[0]=resolved_tools['fzf'] or 'fzf'
        try:
            proc=subprocess.run(arguments,
                    input=''.join(str(i)+'\t'+label+'\n' for i,label in enumerate(labels)),text=True,stdout=subprocess.PIPE,env=child_env)
        except OSError as error:
            raise RuntimeError('fzf could not be started: '+str(error)) from error
        if proc.returncode in (1,130): return None
        if proc.returncode:
            raise RuntimeError('fzf failed (exit '+str(proc.returncode)+')')
        selected=[]
        for row in proc.stdout.splitlines():
            index,sep,label=row.partition('\t')
            if not sep or not index.isascii() or not index.isdigit() or len(index)>8: return None
            n=int(index)
            if n>=len(values) or label!=labels[n]: return None
            if values[n] not in selected: selected.append(values[n])
        if multi: return selected
        return selected[0] if len(selected)==1 else None
