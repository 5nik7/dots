"""Deterministic documentation projection into an independently versioned wiki."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import shutil
import stat
import subprocess
import sys
from urllib.parse import quote, unquote, urlsplit

LIB = Path(__file__).resolve().parent
sys.path.insert(0, str(LIB))
sys.path.insert(0, str(LIB/'files'))
from wiki_presentation import WikiPresentation, report, topics, document, diagnostic
from file_platform import state_root
from transactions import Store, digest, parents_safe, exists

MANIFEST = '.dots/wiki.json'
INVENTORY = '.dots-wiki.json'
PAGE = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]*\Z')
LINK = re.compile(r'(!?\[[^\]\n]*\])\((<[^>\n]+>|[^\s()]+)(\s+"[^"\n]*")?\)')
REFERENCE = re.compile(r'^(\s*\[[^\]]+\]:\s*)(\S+)(.*)$')
LIMIT = 4 * 1024 * 1024


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(data):
    return (json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True)+'\n').encode()


def git(root, *args, required=True):
    if any(k in os.environ for k in ('GIT_DIR','GIT_WORK_TREE','GIT_INDEX_FILE','GIT_COMMON_DIR')):
        raise ValueError('unset Git repository/index redirection variables')
    result = subprocess.run(['git','-C',str(root),*args], capture_output=True,
                            env=dict(os.environ,GIT_OPTIONAL_LOCKS='0'))
    if required and result.returncode: raise ValueError('Git operation failed: '+args[0])
    return result.stdout


class Reader:
    """Read literal source bytes from a working tree, index or committed tree."""
    def __init__(self, root, revision=None):
        self.root, self.revision, self.inputs = Path(root).resolve(), revision, {}
        self.modes = None
        if revision:
            self.modes = {}
            args = ('ls-files','--stage','-z') if revision == ':' else ('ls-tree','-r','-z',revision)
            for row in git(self.root,*args).split(b'\0'):
                if not row: continue
                meta,name = row.split(b'\t',1)
                fields = meta.decode().split()
                if revision == ':' and fields[2] != '0': raise ValueError('unmerged documentation inputs')
                self.modes[name.decode('utf-8')] = fields[0]

    def names(self, prefix):
        if self.modes is not None: return sorted(n for n,mode in self.modes.items() if n.startswith(prefix) and mode in ('100644','100755') and '/' not in n[len(prefix):])
        directory = self.root/prefix.rstrip('/')
        return sorted(p.relative_to(self.root).as_posix() for p in directory.iterdir() if p.is_file() and not p.is_symlink()) if directory.is_dir() else []

    def read(self, name):
        p = PurePosixPath(name)
        if p.is_absolute() or '..' in p.parts or '\\' in name: raise ValueError('source path must stay in the repository')
        if self.modes is not None:
            if self.modes.get(name) not in ('100644','100755'): raise ValueError('missing or nonregular source: '+name)
            data = git(self.root,'show',(':'+name) if self.revision == ':' else self.revision+':'+name)
        else:
            path = self.root/name
            parents_safe(path)
            if not path.is_file() or path.is_symlink() or path.stat().st_size > LIMIT: raise ValueError('missing or nonregular source: '+name)
            data = path.read_bytes()
        if len(data)>LIMIT: raise ValueError('document exceeds size limit: '+name)
        data.decode('utf-8')
        self.inputs[name]=sha(data)
        return data


def manifest(reader):
    data = json.loads(reader.read(MANIFEST))
    if not isinstance(data,dict) or data.get('schema') != 1: raise ValueError('unsupported wiki manifest')
    for key in ('checkout','clone_url','web_url','source_url','source_branch'):
        value=data.get(key)
        if not isinstance(value,str) or not value or any(ord(c)<32 for c in value):
            raise ValueError('wiki manifest requires a nonempty '+key)
    for key in ('web_url','source_url'):
        parsed=urlsplit(data[key])
        if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError('wiki URLs must be credential-free HTTPS URLs')
    if not isinstance(data.get('pages'),list) or not data['pages']: raise ValueError('wiki pages are required')
    seen, sources = set(), set()
    for row in data['pages']:
        if not isinstance(row,dict): raise ValueError('wiki page must be an object')
        identity=row.get('id')
        if not isinstance(identity,str) or not PAGE.fullmatch(identity) or identity.casefold() in seen or identity.casefold()=='agents':
            raise ValueError('duplicate, reserved or invalid page ID: '+str(identity))
        seen.add(identity.casefold())
        if any(not isinstance(row.get(key),str) or not row[key] or any(ord(c)<32 for c in row[key]) for key in ('title','section')):
            raise ValueError('page title and section are required')
        if row.get('source'):
            if not isinstance(row['source'],str): raise ValueError('page source must be a relative path')
            if row['source'] in sources: raise ValueError('duplicate page source')
            sources.add(row['source'])
        elif row.get('generated') != 'commands': raise ValueError('page requires a source or command metadata')
    if not any(row['id']=='Home' for row in data['pages']): raise ValueError('Home page is required')
    if not isinstance(data.get('exclude_docs',[]),list) or any(not isinstance(name,str) for name in data.get('exclude_docs',[])):
        raise ValueError('exclude_docs must be a list of relative paths')
    return data


def checkout(root, data=None):
    data = data or manifest(Reader(root))
    home = os.environ.get('HOME') or os.environ.get('USERPROFILE') or str(Path.home())
    value = os.environ.get('DOTS_WIKI_DIR') or data['checkout'].replace('${HOME}', home)
    path = Path(value).expanduser().absolute()
    if not path.is_absolute() or '${' in str(path): raise ValueError('invalid wiki checkout path')
    primary = Path(root).resolve()
    # A companion must never alias the source tree, its Git metadata or a submodule.
    resolved = path.resolve()
    if resolved == primary or resolved.is_relative_to(primary) or primary.is_relative_to(resolved):
        raise ValueError('wiki must be a separate checkout outside the source repository')
    parents_safe(path)
    if path.is_symlink(): raise ValueError('wiki checkout must not be a symlink')
    return path


def require_checkout(path):
    if not path.is_dir() or not (path/'.git').exists(): raise ValueError('wiki checkout unavailable; use dots wiki init')
    if (path/'.git').is_symlink(): raise ValueError('wiki Git metadata must not be a symlink')
    top = git(path,'rev-parse','--show-toplevel').decode().strip()
    if Path(top).resolve()!=path.resolve(): raise ValueError('wiki path must be a repository root')


def anchors(text):
    from wiki_topics import headings
    return {row['anchor'] for row in headings(text)}


def generate(root, revision=None):
    reader=Reader(root,revision); spec=manifest(reader)
    pages=spec['pages']; by_source={row['source']:row['id'] for row in pages if row.get('source')}
    docs=set(n for n in reader.names('docs/') if n.endswith('.md') and '/' not in n[5:])
    excluded=set(spec.get('exclude_docs',[]))
    unlisted=docs-set(by_source)-excluded
    if unlisted: raise ValueError('documentation missing from wiki manifest: '+', '.join(sorted(unlisted)))
    texts={row['id']:reader.read(row['source']).decode() for row in pages if row.get('source')}
    # Include generator semantics in provenance; staged publication must run the reviewed generator.
    for name in ('lib/dots/wiki.py','lib/dots/command_metadata.py','lib/dots/wiki_commands.py','lib/dots/wiki_topics.py'):
        if (reader.modes is not None and name in reader.modes) or (Path(root)/name).is_file():
            data=reader.read(name)
            if data != (LIB/Path(name).name).read_bytes(): raise ValueError('selected generator differs from running generator; use the matching Dots checkout before building or publishing the wiki')
    from wiki_commands import markdown
    reference = markdown(reader)
    for row in pages:
        if row.get('generated')=='commands': texts[row['id']]=reference
    anchor_map={identity:anchors(text) for identity,text in texts.items()}
    outputs={}; links=[]
    def rewrite(target, source, identity, image=False):
        target=target.strip('<>'); parsed=urlsplit(target)
        if parsed.scheme or parsed.netloc: return target
        if not parsed.path: page=identity; relative=source
        else:
            import posixpath
            relative=posixpath.normpath(posixpath.join(posixpath.dirname(source),unquote(parsed.path)))
            if relative.startswith('../') or relative.startswith('/'): raise ValueError('link escapes repository: '+source+' -> '+target)
            page=by_source.get(relative)
        if page:
            fragment=unquote(parsed.fragment)
            links.append((identity,page,fragment))
            return quote(page,safe='-_')+('#'+parsed.fragment if parsed.fragment else '')
        if not parsed.path: return target
        if reader.modes is None:
            available=os.path.lexists(Path(root)/relative)
        else:
            available=relative in reader.modes or any(n.startswith(relative.rstrip('/')+'/') or mode=='160000' and relative.startswith(n+'/') for n,mode in reader.modes.items())
        if not available: raise ValueError('broken source link: '+source+' -> '+target)
        base=spec['source_url'].rstrip('/')
        return base+('/raw/' if image else '/blob/')+quote(spec.get('source_branch','main'),safe='')+'/'+quote(relative,safe='/')+('#'+parsed.fragment if parsed.fragment else '')
    for row in pages:
        identity=row['id']; source=row.get('source','docs/commands.md'); fence=False; lines=[]
        for line in texts[identity].splitlines():
            if line.lstrip().startswith(('```','~~~')): fence=not fence; lines.append(line); continue
            if not fence:
                line=LINK.sub(lambda m:m[1]+'('+rewrite(m[2],source,identity,m[1].startswith('!'))+(m[3] or '')+')',line)
                match=REFERENCE.match(line)
                if match: line=match[1]+rewrite(match[2],source,identity)+match[3]
            lines.append(line)
        base=spec['source_url'].rstrip('/')
        branch=quote(spec['source_branch'],safe='')
        if row.get('generated'):
            footer='[Command wrappers]('+base+'/tree/'+branch+'/bin) · [Built-in metadata]('+base+'/tree/'+branch+'/lib/dots/metadata)'
        else:
            footer='[Edit source]('+base+'/blob/'+branch+'/'+quote(source,safe='/')+')'
        outputs[identity+'.md']=('<!-- Generated by dots wiki build; edit canonical source. -->\n\n'+'\n'.join(lines).rstrip()+'\n\n---\n'+footer+' · [Home](Home)\n').encode()
    broken=[origin+' -> '+page+'#'+fragment for origin,page,fragment in links if fragment and fragment not in anchor_map[page]]
    if broken: raise ValueError('broken heading links: '+'; '.join(broken))
    sidebar=['[Home](Home)','']; section=None
    for row in pages:
        if row['id']=='Home': continue
        if row['section']!=section:
            section=row['section']
            if sidebar[-1]!='':sidebar.append('')
            sidebar+=['**'+section+'**','']
        sidebar+=['- ['+row['title']+']('+row['id']+')']
    sidebar+=['','---','[Repository]('+spec['source_url']+') · [Issues]('+spec['source_url']+'/issues)','']
    outputs['_Sidebar.md']='\n'.join(sidebar).encode()
    outputs['AGENTS.md']=('''# Wiki maintenance

This checkout contains generated Dots documentation. Edit canonical documents in the main Dots checkout, not generated pages here. `dots wiki path --source` locates that checkout; `dots wiki edit PAGE` opens a page source. Read its AGENTS.md and use the dots-documentation-maintenance and dots-wiki-maintenance skills.

Run `dots wiki build --dry-run`, build, then `dots wiki check`. Preserve unrecognized files and edits; reconcile generated-file drift in the source rather than overwriting it. Keep the sidebar generated from the page manifest. Commit/push only when explicitly requested. `dots git wiki publish` checks the selected content against published source inputs.
''').encode()
    inventory=dict(schema=1,inputs=reader.inputs,outputs={name:sha(data) for name,data in outputs.items()})
    outputs[INVENTORY]=encoded(inventory)
    return spec,outputs,reader


def compare(root, path, revision=None, source_revision=None):
    spec,outputs,_=generate(root,source_revision)
    reader=Reader(path,revision)
    findings=[]
    for name,data in outputs.items():
        try: actual=reader.read(name)
        except (ValueError,OSError): findings.append(dict(page=name,status='missing'));continue
        if actual!=data: findings.append(dict(page=name,status='stale'))
    try:
        old=json.loads(reader.read(INVENTORY))
        for name in old.get('outputs',{}):
            if name not in outputs: findings.append(dict(page=name,status='obsolete'))
    except (ValueError,OSError): pass
    return findings


def build_plan(root,path):
    require_checkout(path)
    spec,outputs,reader=generate(root)
    old={};inventory=path/INVENTORY
    if exists(inventory):
        old=json.loads(Reader(path).read(INVENTORY))
        if old.get('schema')!=1: raise ValueError('unsupported generated inventory')
    operations=[];guards={}
    for name,expected in reader.inputs.items():
        before=digest(root/name)
        actual=Reader(root).read(name)
        after=digest(root/name)
        if before!=after or sha(actual)!=expected: raise ValueError('source changed during generation: '+name)
        guards[str(root/name)]=after
    guards[str(inventory)]=digest(inventory)
    for name in sorted(set(outputs)|set(old.get('outputs',{}))):
        if name!=INVENTORY and name!='AGENTS.md' and name!='_Sidebar.md' and not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*\.md',name): raise ValueError('unsafe generated inventory path')
        target=path/name; parents_safe(target);before=digest(target);guards[str(target)]=before
        current=Reader(path).read(name) if before is not None else None
        desired=outputs.get(name)
        if current==desired: continue
        known=old.get('outputs',{}).get(name)
        if current is not None and name!=INVENTORY:
            starter=name=='Home.md' and not old and current==b'Welcome to the dots wiki!\n'
            if not starter and (known is None or sha(current)!=known): raise ValueError('generated page has unrecognized edits; reconcile source first: '+name)
        operations.append(dict(path=str(target),text=desired.decode()) if desired is not None else dict(path=str(target),delete=True))
    return operations,guards


def approve(args,label):
    if args.yes:return True
    if not sys.stdin.isatty(): raise ValueError('use --yes to approve '+label+' without a terminal')
    from interaction import gum_confirm
    answer=gum_confirm(label+'?', 'Apply')
    if answer is not None:return answer
    return input(label+'? [y/N] ').lower()=='y'


def initialize(path,spec):
    # Acquisition has a journal and publishes a complete clone without replacing any target.
    from bootstrap import publish_checkout
    import tempfile
    from file_platform import lock
    source=spec['clone_url'];parsed=urlsplit(source)
    if not (Path(source).is_absolute() or parsed.scheme=='https') or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError('wiki clone source must be a local repository or credential-free HTTPS')
    parents_safe(path)
    if exists(path): raise ValueError('wiki destination already exists')
    path.parent.mkdir(parents=True,exist_ok=True)
    fd=os.open(path.parent/('.'+path.name+'.init.lock'),os.O_CREAT | os.O_RDWR | getattr(os,'O_NOFOLLOW',0),0o600)
    with os.fdopen(fd,'a+b') as handle:
        lock(handle)
        if exists(path): raise ValueError('wiki destination became occupied')
        work=Path(tempfile.mkdtemp(prefix='.'+path.name+'.init-',dir=path.parent))
        record=dict(schema=1,destination=str(path),status='preparing')
        def save():
            from catalog import atomic_json
            atomic_json(work/'journal.json',record)
        save()
        try:
            result=subprocess.run(['git','-c','protocol.ext.allow=never','-c','submodule.recurse=false','clone','--no-recurse-submodules','--',source,str(work/'checkout')],capture_output=True,timeout=90,env=dict(os.environ,GIT_TERMINAL_PROMPT='0',GCM_INTERACTIVE='Never'))
            if result.returncode:raise ValueError('wiki clone failed; staging journal retained')
            require_checkout(work/'checkout');record['status']='prepared';save()
            publish_checkout(work/'checkout',path)
            record['status']='complete';save()
        except BaseException:
            record['status']='failed';save();raise
        return str(work/'journal.json')


def parser():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='action')
    for action in ('list','show','search','browse','open','edit','path','check','build','init'):
        command=sub.add_parser(action)
        if action in ('show','edit'):command.add_argument('page')
        if action in ('path','open'):command.add_argument('page',nargs='?')
        if action=='search':
            command.add_argument('query')
            modes = command.add_mutually_exclusive_group()
            modes.add_argument('--titles',action='store_true')
            modes.add_argument('--topics',action='store_true')
        if action=='browse':command.add_argument('--query')
        if action=='list':command.add_argument('--section')
        if action in ('show','path'):command.add_argument('--source',action='store_true')
        if action=='show':command.add_argument('--raw',action='store_true')
        if action=='open':command.add_argument('--print-url',action='store_true')
        if action=='check':command.add_argument('--source-only',action='store_true')
        if action in ('build','init'):
            command.add_argument('--dry-run',action='store_true');command.add_argument('--yes',action='store_true')
        if action in ('list','search','check','build','init'):command.add_argument('--json',action='store_true',default=argparse.SUPPRESS)
    p.add_argument('--json',action='store_true')
    return p


def main(argv=None):
    argv=list(sys.argv[1:] if argv is None else argv)
    if argv[:1]==['__names']:
        root=Path(os.environ.get('DOTS') or LIB.parents[1]).resolve()
        field='section' if argv[1:] == ['wiki-section'] else 'id'
        for value in dict.fromkeys(row[field] for row in manifest(Reader(root))['pages']):
            if not any(ord(c)<32 for c in value): print(value)
        return 0
    args=parser().parse_args(argv);action=args.action or 'overview'
    root=Path(os.environ.get('DOTS') or LIB.parents[1]).resolve()
    spec=manifest(Reader(root))
    source_view = action == 'browse' or action == 'search' and args.topics
    path = None if source_view else checkout(root,spec)
    ui=WikiPresentation()
    rows=spec['pages'];page=getattr(args,'page',None)
    row=next((r for r in rows if r['id']==page),None) if page else None
    if page and row is None:raise ValueError('unknown wiki page: '+page+'; use dots wiki list')
    as_json=getattr(args,'json',False)
    from progress import configure, Progress
    configure(action in ('build', 'init') and not as_json and not getattr(args, 'dry_run', False))
    def emit(data):
        if as_json:print(json.dumps(dict(schema=1,**data),ensure_ascii=True));return
        report(ui,action,data,root)
    if action=='path':
        if getattr(args,'source',False):
            if row and not row.get('source'):raise ValueError('generated command reference has no single source file')
            print(root/row['source'] if row else root)
        else:print(path/(page+'.md') if page else path)
    elif action=='open':
        url=spec['web_url'].rstrip('/')+'/'+quote(page or 'Home',safe='-_')
        if args.print_url:print(url)
        else:
            import webbrowser
            if not webbrowser.open(url):raise ValueError('browser unavailable; use dots wiki open --print-url')
    elif action=='edit':
        if not row.get('source'):raise ValueError('edit command metadata in Dots; this page has no single source')
        Reader(root).read(row['source'])
        editor=os.environ.get('VISUAL') or os.environ.get('EDITOR') or next((x for x in ('nvim','vim','nano','notepad') if shutil.which(x)),None)
        if not editor:raise ValueError('set VISUAL or EDITOR to edit documentation')
        command=shlex.split(editor,posix=os.name!='nt')
        if os.name=='nt':command=[part[1:-1] if len(part)>1 and part[0]==part[-1] and part[0] in ('\"',"'") else part for part in command]
        return subprocess.call([*command,str(root/row['source'])])
    elif action == 'browse':
        if not sys.stdin.isatty() or not sys.stdout.isatty():
            raise ValueError('browse requires a terminal; use dots wiki search QUERY --topics or show PAGE --source')
        from wiki_browser import browse
        return browse(root, args.query, ui)
    elif action == 'show':
        if getattr(args,'source',False):
            if not row.get('source'):raise ValueError('page is generated from command metadata')
            data=Reader(root).read(row['source'])
        else:require_checkout(path);data=Reader(path).read(row['id']+'.md')
        if sys.stdout.isatty() and not getattr(args,'raw',False):
            sys.stdout.buffer.write(document(data,ui))
        else:sys.stdout.buffer.write(data)
    elif action=='list':
        if args.section:rows=[r for r in rows if r['section'].casefold()==args.section.casefold()]
        emit(dict(items=[dict(r,status='available' if (path/(r['id']+'.md')).is_file() and not (path/(r['id']+'.md')).is_symlink() else 'missing') for r in rows]))
    elif action=='search' and args.topics:
        from wiki_topics import snapshot, search
        _, records = snapshot(root)
        matches = search(records, args.query)
        if as_json:
            print(json.dumps(dict(schema=1,mode='topics',query=args.query,items=matches),ensure_ascii=True))
        else:
            topics(ui,args.query,matches)
        return 0 if matches else 1
    elif action=='search':
        require_checkout(path);matches=[]
        for item in rows:
            text=item['title'] if args.titles else Reader(path).read(item['id']+'.md').decode()
            for n,line in enumerate(text.splitlines(),1):
                if args.query.casefold() in line.casefold():matches.append(dict(page=item['id'],line=n,text=line))
        emit(dict(items=matches));return 0 if matches else 1
    elif action=='check':
        generate(root)
        findings=[] if args.source_only else compare(root,path)
        emit(dict(healthy=not findings,source_only=args.source_only,items=findings));return int(bool(findings))
    elif action=='build':
        operations,guards=build_plan(root,path)
        if args.dry_run:emit(dict(status='preview',items=[op['path'] for op in operations]));return 0
        if not operations:emit(dict(status='unchanged',items=[]));return 0
        if not as_json:emit(dict(status='planned',items=[op['path'] for op in operations]))
        if not approve(args,'Build wiki pages'):emit(dict(status='cancelled',items=[]));return 0
        with Progress('Building wiki pages'):
            record=Store(state_root()).apply('wiki-build',operations,guards,retain=True)
        emit(dict(status='built',transaction=record['id'],items=[op['path'] for op in operations]))
    elif action=='init':
        if exists(path):require_checkout(path);emit(dict(status='available',path=str(path)));return 0
        if args.dry_run:emit(dict(status='preview',path=str(path)));return 0
        if not approve(args,'Clone wiki checkout'):emit(dict(status='cancelled'));return 0
        with Progress('Cloning wiki checkout'):
            journal=initialize(path,spec)
        emit(dict(status='cloned',path=str(path),journal=journal))
    else:
        branch=git(path,'symbolic-ref','--quiet','--short','HEAD',required=False).decode().strip() if (path/'.git').exists() else ''
        findings=compare(root,path)
        emit(dict(path=str(path),branch=branch or 'unavailable',freshness='current' if not findings else 'missing or stale',items=[dict(id=r['id'],title=r['title'],section=r['section']) for r in rows],commands='show PAGE · search QUERY · check · build · dots git wiki status'))
    return 0


if __name__=='__main__':
    try:sys.exit(main())
    except (ValueError,OSError,subprocess.SubprocessError) as error:
        diagnostic(error,sys.stderr);sys.exit(1)
    except KeyboardInterrupt:sys.exit(130)
