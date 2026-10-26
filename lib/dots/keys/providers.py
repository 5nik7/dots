"""Bounded native observations and conservative configuration readers."""
import gzip
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import stat
import subprocess
import tomllib
from .model import APPS, record, readable, merge

LIMIT=2*1024*1024


def read_file(path):
    fd=os.open(path,os.O_RDONLY|getattr(os,'O_NONBLOCK',0))
    with os.fdopen(fd,'rb') as stream:
        info=os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size>LIMIT:raise ValueError('not a bounded regular configuration file')
        data=stream.read(LIMIT+1)
        if len(data)>LIMIT:raise ValueError('configuration exceeds read limit')
    return data.decode('utf8')


def run(args):
    # These commands only expose native binding metadata, never user rc scripts.
    result=subprocess.run(args,capture_output=True,timeout=8,env=dict(os.environ,LC_ALL='C.UTF-8'))
    if result.returncode:raise ValueError('native binding query unavailable')
    if len(result.stdout)>LIMIT:raise ValueError('native binding query exceeds limit')
    return result.stdout.decode('utf8','replace')


def shell_dump(app, mode, text, evidence='live', source=None):
    rows=[]
    for number,line in enumerate(text.splitlines(),1):
        try:parts=shlex.split(line)
        except ValueError:continue
        if app=='zsh' and len(parts)>=3 and parts[0]=='bindkey':
            args=parts[1:];kind='widget';m=mode or 'main'
            while args and args[0] in ('-R','-s','-M','-a'):
                option=args.pop(0)
                if option=='-M':
                    if not args:break
                    m=args.pop(0)
                elif option=='-a':m='vicmd'  # bindkey -L abbreviates -M vicmd.
                elif option=='-s':kind='macro'
                else:kind='range'
            if len(args)!=2:continue
            if args[-1] in ('undefined-key','self-insert') or evidence=='configured' and any('$' in p or '`' in p for p in args):continue
            rows.append(record(app,m,args[0],args[1] if kind=='widget' else 'Keyboard macro' if kind=='macro' else args[1],
                               evidence=evidence,source=source,line=number if source else None,kind=kind))
        elif app=='bash':
            match=re.fullmatch(r'"((?:\\.|[^"\\])*)":\s*(.+)',line)
            if not match or match[2] in ('self-insert','do-lowercase-version'):continue
            action='Keyboard macro' if match[2].startswith('"') or mode.endswith(':commands') else match[2]
            rows.append(record(app,mode.removesuffix(':commands'),match[1],action,evidence=evidence,source=source,
                               line=number if source else None))
    return rows


def snapshot(raw, kind):
    if len(raw)>8*LIMIT:raise ValueError('live snapshot exceeds limit')
    if kind=='shell':
        fields=raw.decode('utf8','replace').split('\0');rows=[];apps=set()
        if fields[-1]!='' or (len(fields)-1)%3:raise ValueError('invalid shell snapshot')
        for i in range(0,len(fields)-1,3):
            app,mode,data=fields[i:i+3]
            if app not in ('zsh','bash'):raise ValueError('unsupported live shell')
            apps.add(app);rows+=shell_dump(app,mode,data)
        return rows,apps
    data=json.loads(raw.decode('utf-8-sig'))
    if data.get('version')!=1 or data.get('app') not in ('nvim','powershell') or not isinstance(data.get('rows'),list):
        raise ValueError('invalid native binding snapshot')
    rows=[];app=data['app']
    for item in data['rows'][:20000]:
        if not isinstance(item,dict) or not all(isinstance(item.get(k),str) for k in ('key','mode','action')):raise ValueError('invalid binding record')
        rows.append(record(app,item['mode'],item['key'],item['action'],str(item.get('description') or ''),'live',
                           item.get('source'),item.get('line'),scope=item.get('scope','global')))
    return rows,{app}


def config_root(root, app, windows=None):
    from files.app_paths import config_directory, television_config_directory
    windows=os.name=='nt' if windows is None else windows
    home=Path.home();explicit=False
    base=Path(os.environ.get('XDG_CONFIG_HOME') or home/'.config')
    if app=='television':
        candidate=television_config_directory(windows=windows)
        explicit=bool(os.environ.get('DOTS_APP_TELEVISION_CONFIG') or os.environ.get('TELEVISION_CONFIG'))
    elif app=='yazi' and windows:
        candidate=config_directory('yazi')
        explicit=bool(os.environ.get('DOTS_APP_YAZI_CONFIG') or os.environ.get('YAZI_CONFIG_HOME'))
    else:
        variable={'yazi':'YAZI_CONFIG_HOME','kitty':'KITTY_CONFIG_DIRECTORY','nvim':'NVIM_APPNAME'}.get(app)
        value=os.environ.get(variable) if variable else None
        if app=='nvim' and windows:base=Path(os.environ.get('LOCALAPPDATA') or home/'AppData/Local')
        candidate=(base/value if app=='nvim' else Path(value).expanduser()) if value else base/app
        explicit=bool(value)
    return candidate if explicit or candidate.is_dir() else root/'config'/app


def toml_rows(path,app,default=False):
    data=tomllib.loads(read_file(path));rows=[]
    if app=='yazi':
        return yazi_declarations(data,path,default)
    else:
        sections=[('picker',data.get('keybindings',{})),('shell integration',data.get('shell_integration',{}).get('keybindings',{}))]
        for mode,bindings in sections:
            for key,action in bindings.items():
                rows.append(record(app,mode,key,json.dumps(action) if not isinstance(action,str) else action,source=path,default=default))
    return rows


def yazi_declarations(data,path,default=False):
    rows=[]
    for mode,section in data.items():
        if not isinstance(section,dict):continue
        for name in ('prepend_keymap','keymap','append_keymap'):
            entries=section.get(name,[])
            if not isinstance(entries,list):raise ValueError('Yazi keymap table must be an array')
            for item in entries:
                if not isinstance(item,dict):raise ValueError('Invalid Yazi keymap entry')
                key=item.get('on');action=item.get('run','');description=item.get('desc','')
                if not isinstance(key,(str,list)) or isinstance(key,list) and (not key or not all(isinstance(k,str) for k in key)):
                    raise ValueError('Invalid Yazi binding notation')
                if not isinstance(action,(str,list)) or isinstance(action,list) and not all(isinstance(a,str) for a in action) or not isinstance(description,str):
                    raise ValueError('Invalid Yazi binding action or description')
                rows.append(record('yazi',mode,key,'; '.join(action) if isinstance(action,list) else action,
                                   description,source=path,default=default,layer=name))
    return rows


def yazi_rows(root,notes,defaults=True):
    baseline=Path(__file__).parent/'data/yazi-default.toml'
    rows=toml_rows(baseline,'yazi',True)
    if defaults:notes.append('Bundled Yazi shipped defaults: 8dd895c695a5950330c2623eb43debf323b60654; installed-version compatibility is unverified.')
    path=config_root(root,'yazi')/'keymap.toml'
    data={}
    try:
        if path.is_file():
            data=tomllib.loads(read_file(path))
            custom=yazi_declarations(data,path)
            rows+=custom
        else:notes.append('No readable configuration at '+str(path))
    except (ValueError,OSError,UnicodeError):
        notes.append('Yazi configuration could not be read; bundled defaults remain available.')
        data={}
    replaced={mode for mode,section in data.items() if isinstance(section,dict) and 'keymap' in section}
    # Yazi compares the first two strokes when combining its three tables.
    def identity(row):
        key=row['key'] if isinstance(row['key'],list) else [row['key']]
        return row['mode'],tuple(readable(k) for k in key[:2])
    prepended={identity(r) for r in rows if r['layer']=='prepend_keymap'}
    base={identity(r) for r in rows if r['layer']=='keymap' and not (r['default'] and r['mode'] in replaced)}
    for row in rows:
        key=identity(row)
        shadowed=(row['default'] and row['mode'] in replaced or
                  row['layer']=='keymap' and key in prepended or
                  row['layer']=='append_keymap' and key in base)
        row['status']='shadowed' if shadowed else 'configured; activation unverified'
    notes.append('Prepend/replacement/append tables are compared statically; conditional and running-app activation is unverified.')
    return rows if defaults else [r for r in rows if not r['default']]


def kitty_rows(path,notes,seen=None,default=False):
    seen=seen if seen is not None else set();resolved=path.resolve()
    if resolved in seen:return []
    if len(seen)>=32:notes.append('Kitty include limit reached.');return []
    seen.add(resolved);rows=[]
    for number,line in enumerate(read_file(path).splitlines(),1):
        try:parts=shlex.split(line,comments=True)
        except ValueError:continue
        if not parts:continue
        if parts[0]=='include' and len(parts)==2:
            value=os.path.expandvars(os.path.expanduser(parts[1]));target=Path(value)
            if not target.is_absolute():target=path.parent/target
            if any(c in value for c in '*?['):notes.append('Kitty wildcard include not expanded: '+str(target));continue
            if target.is_file():rows+=kitty_rows(target,notes,seen,default)
        elif parts[0]=='map' and len(parts)>=3:
            rest=parts[1:];mode='normal'
            while rest and rest[0].startswith('--'):
                option=rest.pop(0)
                if option.startswith('--mode='):mode=option.partition('=')[2]
            if len(rest)>=2:rows.append(record('kitty',mode,rest[0].split('>'),' '.join(rest[1:]),source=path,line=number,default=default))
        elif parts[0] in ('globinclude','envinclude','geninclude'):notes.append('Dynamic Kitty include omitted: '+parts[0])
    return rows


def split_bindings(value):
    depth=0;start=0;escaped=False
    for i,char in enumerate(value):
        if escaped:escaped=False;continue
        if char=='\\':escaped=True;continue
        if char in '([{':depth+=1
        elif char in ')]}':depth=max(0,depth-1)
        elif char==',' and not depth:yield value[start:i];start=i+1
    yield value[start:]


def fzf_rows(root):
    rows=[];notes=[]
    if os.environ.get('FZF_DEFAULT_OPTS_FILE'):
        notes.append('FZF_DEFAULT_OPTS_FILE is not inspected; bindings from that file are outside this snapshot.')
    values=[]
    for name in ('FZF_DEFAULT_OPTS','FZF_CTRL_R_OPTS','FZF_CTRL_T_OPTS','FZF_ALT_C_OPTS'):
        try:parts=shlex.split(os.environ.get(name,''))
        except ValueError:notes.append(name+' cannot be parsed as literal options.');continue
        for i,part in enumerate(parts):
            if part.startswith('--bind='):values.append((name,part[7:]))
            elif part=='--bind' and i+1<len(parts):values.append((name,parts[i+1]))
    if os.environ.get('_FZF_BINDS_') and not any(context=='FZF_DEFAULT_OPTS' for context,_ in values):values.append(('_FZF_BINDS_',os.environ['_FZF_BINDS_']))
    if not values:
        source=root/'shells/shared/fzf.sh'
        if source.is_file():
            text=read_file(source).replace('\\\n','')
            match=re.search(r'export _FZF_BINDS_=["\']([^"\']*)["\']',text)
            if match:values.append((str(source),match[1]))
    for context,value in values:
        for binding in split_bindings(value):
            key,sep,action=binding.strip().partition(':')
            if not sep:continue
            # External action payloads may contain credentials or executable code.
            action=re.sub(r'(execute(?:-silent)?|reload(?:-sync)?|become|transform[\w-]*)\(.*',r'\1 (command omitted)',action)
            mode={'FZF_CTRL_R_OPTS':'history picker','FZF_CTRL_T_OPTS':'file picker','FZF_ALT_C_OPTS':'directory picker'}.get(context,'picker')
            rows.append(record('fzf',mode,key,action,source=context))
    notes.append('FZF rows describe exported/configured options, not an already-running picker; per-invocation options may override them.')
    return rows,notes


def nvim_rows(directory,notes):
    rows=[];paths=list((directory/'lua/config').glob('*.lua'))+list((directory/'lua/plugins').glob('*.lua'))
    for path in paths[:256]:
        text=read_file(path)
        for number,line in enumerate(text.splitlines(),1):
            if line.lstrip().startswith('--'):continue
            # Only literal declarations; Lua expressions are never evaluated.
            found=re.search(r'''(?:vim\.keymap\.set|vim\.api\.nvim_set_keymap)\(\s*["']([^"']+)["']\s*,\s*["']([^"']+)["']\s*,\s*["']([^"']*)["']''',line)
            if found:
                desc=re.search(r'''desc\s*=\s*["']([^"']*)["']''',line)
                rows.append(record('nvim',found[1],found[2],found[3],desc[1] if desc else '',source=path,line=number))
            # A literal lazy.nvim keys entry with an authored description.
            elif 'desc' in line:
                found=re.search(r'''\{\s*["']([^"']+)["']\s*,\s*["']([^"']*)["'].*?desc\s*=\s*["']([^"']*)["']''',line)
                if found:
                    modes=['n']
                    if re.search(r'\bmode\s*=',line):
                        mode=re.search(r'''\bmode\s*=\s*(?:["']([^"']+)["']|\{([^}]*)\})''',line)
                        if not mode:continue
                        modes=[mode[1]] if mode[1] else re.findall(r'''["']([^"']+)["']''',mode[2])
                    for mode in modes:
                        rows.append(record('nvim',mode,found[1],found[2],found[3],source=path,line=number))
    notes.append('Neovim configuration coverage is literal declarations only. Use :DotsKeys in the target buffer for effective plugin and buffer mappings.')
    return rows


def tmux_rows():
    if not shutil.which('tmux'):return [],['tmux is not installed; live tables unavailable.']
    try:
        text=run(['tmux','-N','-u','list-keys'])
        format='dots-keys\t#{q|a:key_table}\t#{q|a:key_string}\t#{q|a:key_note}'
        described=run(['tmux','-N','-u','list-keys','-F',format]);notes_by_key={}
        for line in described.splitlines():
            fields=line.split('\t')
            if len(fields)!=4 or fields[0]!='dots-keys':raise ValueError('unsupported tmux metadata format')
            decoded=[]
            for field in fields[1:]:
                words=shlex.split(field)
                if len(words)>1:raise ValueError('invalid quoted tmux metadata')
                decoded.append(words[0] if words else '')
            notes_by_key[tuple(decoded[:2])]=decoded[2]
        prefixes=[]
        target=['-t',os.environ['TMUX_PANE']] if os.environ.get('TMUX_PANE') else ['-g']
        for option in ('prefix','prefix2'):
            value=run(['tmux','-N','show-options','-v',*target,option]).strip()
            if value and value!='None':prefixes.append(readable(value))
    except (ValueError,OSError,subprocess.TimeoutExpired):return [],['No readable running tmux server.']
    rows=[]
    for line in text.splitlines():
        try:parts=shlex.split(line)
        except ValueError:continue
        if not parts or parts.pop(0) not in ('bind-key','bind'):continue
        mode='prefix';note=''
        while parts and parts[0] in ('-T','-N','-r','-n'):
            option=parts.pop(0)
            if option in ('-T','-N') and parts:
                value=parts.pop(0)
                if option=='-T':mode=value
                else:note=value
            elif option=='-n':mode='root'
        if len(parts)<2:continue
        key=parts.pop(0);action=' '.join(parts);note=notes_by_key.get((mode,key),note)
        # Shell payloads are not required to identify a binding's purpose.
        if parts[0] in ('run-shell','run','if-shell','if'):action=parts[0]+' (command omitted)'
        row=record('tmux',mode,key,action,note,'live',scope='server')
        if mode=='prefix':row['display']=(' / '.join(prefixes) or 'Prefix')+' → '+row['display']
        rows.append(row)
    return rows,[]


def shell_config(root,app,notes):
    rows=[]
    if app=='bash':
        path=Path(os.environ.get('INPUTRC') or Path.home()/'.inputrc')
        if path.is_file():rows+=shell_dump('bash','configured',read_file(path),'configured',path)
    paths=list((root/'shells'/app).glob('**/*.zsh' if app=='zsh' else '**/*.bash'))
    from profiles import resolve
    for layer in resolve(root)['layers']:
        paths.append(Path(layer['root'])/'shells'/app/('local.zsh' if app=='zsh' else 'local.bash'))
    paths=[p for p in paths if p.is_file()]
    if app=='zsh' and (Path.home()/'.zshrc.local').is_file():paths.append(Path.home()/'.zshrc.local')
    seen=set()
    for path in paths[:256]:
        if path.resolve() in seen:continue
        seen.add(path.resolve());text=read_file(path)
        if app=='zsh':rows+=shell_dump(app,'main',text,'configured',path)
        else:
            for number,line in enumerate(text.splitlines(),1):
                try:parts=shlex.split(line,comments=True)
                except ValueError:continue
                if not parts or parts.pop(0)!='bind':continue
                mode='emacs-standard';commands=False
                if parts[:1]==['-m'] and len(parts)>2:mode=parts[1];parts=parts[2:]
                if parts[:1]==['-x']:commands=True;parts=parts[1:]
                if len(parts)!=1 or '$' in parts[0]:continue
                found=shell_dump('bash',mode+(':commands' if commands else ''),parts[0],'configured',path)
                for row in found:row['line']=number
                rows+=found
    notes.append(app+' configured rows omit dynamic declarations. Reload Dots shell integration and run dots keys for caller keymaps.')
    return rows


def fzf_defaults(notes):
    executable=shutil.which('fzf')
    if not executable:return []
    base=Path(executable).resolve().parent.parent
    candidates=[base/'man/man1/fzf.1',base/'share/man/man1/fzf.1',base/'share/man/man1/fzf.1.gz']
    version=run([executable,'--version']).split()[0]
    for path in candidates:
        if not path.is_file():continue
        if path.suffix=='.gz':
            # Limit decompression, including malformed or unexpectedly large docs.
            with gzip.open(path,'rt',encoding='utf8') as stream:text=stream.read(LIMIT+1)
            if len(text)>LIMIT:continue
        else:text=read_file(path)
        if 'fzf '+version not in text:continue
        rows=[]
        for match in re.finditer(r'(?m)^    \\fB([^\\\n]+(?:\\-[^\\\n]+)*)\\fR +\\fI([^\n]+?)\\fR',text):
            action=match[1].replace('\\-','-')
            for key in match[2].replace('\\-','-').split():
                if re.fullmatch(r'[a-z0-9+-]+',key):rows.append(record('fzf','picker',key,action,source=path,default=True))
        if rows:return rows
    notes.append('No matching installed FZF default-binding table was found.')
    return []


def installed_defaults(app,notes):
    roots=[Path(os.environ.get('PREFIX','/usr'))/'share',Path('/usr/local/share')]
    rows=[]
    for base in roots:
        candidates={'television':[base/'television/config.toml'],
                    'kitty':[base/'kitty/kitty.conf']} .get(app,[])
        for path in candidates:
            if path.is_file():
                rows+=kitty_rows(path,notes,default=True) if app=='kitty' else toml_rows(path,app,True)
                return rows
    notes.append(app+' defaults are unavailable as supported installed data; no defaults are guessed.')
    return rows


def collect(root,app=None,live_rows=(),live_apps=(),defaults=True):
    wanted=(app,) if app else APPS;rows=[r for r in live_rows if r['app'] in wanted];coverage=[]
    for name in wanted:
        notes=[];before=len(rows)
        try:
            if name in ('zsh','bash'):
                rows+=shell_config(root,name,notes)
                if name in live_apps:notes=['Captured the invoking '+name+' keymaps; printable self-insert and undefined keys omitted.']
            elif name=='powershell':
                if name not in live_apps:notes.append('Invoke dots keys from integrated PowerShell for live PSReadLine mappings.')
            elif name=='tmux':
                found,notes=tmux_rows();rows+=found
            elif name=='fzf':
                found,notes=fzf_rows(root);rows+=found
                if defaults:rows+=fzf_defaults(notes)
            elif name=='nvim':
                rows+=nvim_rows(config_root(root,name),notes)
                notes.append('Unmapped built-in editor commands are not keymap records; live capture covers mappings installed so far.')
            elif name=='yazi':
                rows+=yazi_rows(root,notes,defaults)
            elif name=='codex':
                from .codex import codex_rows
                rows+=codex_rows(notes,defaults)
            else:
                if defaults:rows+=installed_defaults(name,notes)
                directory=config_root(root,name)
                path=directory/('kitty.conf' if name=='kitty' else 'config.toml')
                if path.is_file():rows+=kitty_rows(path,notes) if name=='kitty' else toml_rows(path,name)
                else:notes.append('No readable configuration at '+str(path))
        except (ValueError,OSError,UnicodeError,subprocess.TimeoutExpired) as error:notes.append('Partial coverage: '+str(error))
        count=len([r for r in rows if r['app']==name])
        coverage.append(dict(app=name,count=count,live=any(r['app']==name and r['evidence']=='live' for r in rows),notes=notes))
    rows=merge(rows)
    for item in coverage:item['count']=sum(r['app']==item['app'] for r in rows)
    return dict(version=1,rows=rows,coverage=coverage)
