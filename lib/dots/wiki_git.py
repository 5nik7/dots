"""Wiki association hooks for existing Git workflow and inspection controllers."""
import os
from pathlib import Path
import sys
from urllib.parse import urlsplit

LIB=Path(__file__).resolve().parent
sys.path.insert(0,str(LIB))
from wiki import Reader, MANIFEST, manifest, checkout, require_checkout, compare, git, sha


def core():
    import importlib.util
    name='_dots_wiki_git_core'
    if name not in sys.modules:
        spec=importlib.util.spec_from_file_location(name,LIB/'git/cli.py')
        module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module)
    return sys.modules[name]


def sibling_identity(base, check_push=False):
    """Use local fetch identities and require a real adjacent checkout."""
    sibling = base.with_name(base.name + '.wiki') if base.name else None
    if not sibling or sibling.is_symlink() or not sibling.is_dir():
        return None
    metadata = sibling/'.git'
    if metadata.is_symlink() or not (metadata.is_dir() or metadata.is_file()):
        return None
    if str(LIB/'git') not in sys.path:
        sys.path.insert(0, str(LIB/'git'))
    from inspection import Inspection
    from queries import parse_remote, remote_fields
    engine = core()
    if engine.root(sibling) != sibling:
        return None
    aliases = Inspection(base).aliases

    def identity(path, push=False):
        branch = engine.text(path, 'symbolic-ref', '--quiet', '--short', 'HEAD', required=False)
        remote = remote_fields(path, branch, None, aliases)
        if push:
            urls = engine.text(path, 'remote', 'get-url', '--push', '--all', '--', remote['remote'], required=False)
            if not urls or '\n' in urls:
                return None
            remote = parse_remote(urls, aliases)
        protocol, host, owner = (remote[k] for k in ('protocol', 'host', 'owner'))
        ports = {'ssh': 22, 'https': 443, 'http': 80, 'git': 9418}
        if (protocol not in ports or not host or not owner or not remote['repo']
                or any(ord(ch) < 32 or ord(ch) == 127 for ch in remote['url'])):
            return None
        try:
            port = urlsplit(remote['url']).port if '://' in remote['url'] else None
        except ValueError:
            return None
        if port == 0:
            return None
        endpoint = (protocol, port) if port is not None and port != ports[protocol] else ()
        return host, endpoint, owner, remote['repo']

    source, wiki = identity(base), identity(sibling)
    if source and not source[-1].endswith('.wiki') and wiki == (*source[:-1], source[-1] + '.wiki'):
        if not check_push or wiki == identity(sibling, push=True):
            return source
    return None


def association(base, siblings=True):
    if not os.path.lexists(base/MANIFEST):
        if siblings and sibling_identity(base):
            return dict(path=str(base.with_name(base.name + '.wiki')), kind='wiki', availability='available', reason='')
        return None
    spec=manifest(Reader(base));path=checkout(base,spec)
    if not path.exists():return dict(path=str(path),kind='wiki',availability='missing',reason='use dots wiki init')
    require_checkout(path)
    return dict(path=str(path),kind='wiki',availability='available',reason='')


class Companion:
    def __init__(self,workflow):
        self.workflow=workflow;self.source=workflow.root
        self.only=getattr(workflow.args,'wiki_only',False)
        self.declared = os.path.lexists(self.source/MANIFEST)
        self.row=association(self.source, siblings=self.only or workflow.args.command == 'status')
        self.identity = sibling_identity(self.source) if self.row and not self.declared and workflow.args.command != 'status' else None
        if self.only and (not self.row or self.row['availability']!='available'):
            raise ValueError('wiki checkout unavailable; use dots wiki init')
        self.path=Path(self.row['path']) if self.row else None
        self.snapshot=None
        self.definition=sha(Reader(self.source).read(MANIFEST)) if self.row and self.declared else None
        if self.only:workflow.root=self.path

    def recheck(self):
        if not self.declared:
            if not self.identity or os.path.lexists(self.source/MANIFEST) or sibling_identity(self.source, check_push=self.workflow.args.command == 'publish') != self.identity:
                raise ValueError('wiki association changed; inspect it and rerun')
            return
        current=association(self.source, siblings=False)
        if not current or current['path']!=str(self.path) or current['availability']!='available':
            raise ValueError('wiki association changed; inspect it and rerun')

    def collect(self):
        w=self.workflow
        if not self.row:return
        if self.row['availability']!='available':
            w.event(self.path,'skipped','Wiki checkout unavailable; use dots wiki init');return
        if not self.only:w.collect(self.path)
        self.snapshot=w.fingerprint(self.source)
        try:self.validate(False)
        except (ValueError,OSError) as error:
            w.blocked.add(self.path);w.event(self.path,'blocked',str(error))

    def validate(self, executing):
        w=self.workflow
        if not self.row or self.row['availability']!='available':return
        if not self.declared:
            self.recheck()
            return
        if sha(Reader(self.source).read(MANIFEST))!=self.definition or association(self.source)['path']!=str(self.path):
            raise ValueError('wiki association changed after preview')
        if executing and not self.only:
            if self.source in w.blocked or any(e['path']==str(self.source) and e['status'] in ('blocked','failed') for e in w.events):
                raise ValueError('source publication failed; wiki publication is blocked')
            if not any(e['path']==str(self.source) and e['status']=='published' for e in w.events) and w.fingerprint(self.source)!=self.snapshot:
                raise ValueError('source inputs changed after preview')
        upstream=core().upstream
        configured_branch=manifest(Reader(self.source)).get('source_branch','main')
        if upstream(self.source)[2]!='refs/heads/'+configured_branch:
            raise ValueError('wiki publication requires the configured source branch: '+configured_branch)
        if self.only or executing:
            _,remote,ref,tracking=upstream(self.source)
            # A real wiki-only publication refreshes its source evidence. A root publication
            # has already refreshed this tracking ref using its verified push destination.
            if executing and (self.only or not any(e['path']==str(self.source) and e['status']=='published' for e in w.events)):
                w.fetch(self.source,remote,ref,tracking)
            source_revision=tracking
        else:
            source_revision=None if w.args.all else ':'
        wiki_revision=None if w.args.all else ':'
        findings=compare(self.source,self.path,revision=wiki_revision,source_revision=source_revision)
        if findings:raise ValueError('selected wiki content is stale; run dots wiki build, then stage the source and generated files: '+', '.join(r['page'] for r in findings[:4]))


def main(argv=None):
    argv=list(sys.argv[1:] if argv is None else argv)
    action=argv.pop(0) if argv and argv[0] in ('info','status','sync','publish') else 'info'
    sys.path.insert(0,str(LIB/'git'))
    if action=='info':
        from help_adapters import HelpArgumentParser
        import inspection
        p=HelpArgumentParser(add_help=False);p.add_argument('-C','--directory',default=os.environ.get('DOTS',str(LIB.parents[1])))
        args,rest=p.parse_known_args(argv)
        base=inspection.context(args.directory);row=association(base)
        if not row or row['availability']!='available':raise ValueError('wiki checkout unavailable; use dots wiki init')
        return inspection.main(['info','-C',row['path'],'--no-wiki',*rest], report_kind='wiki')
    cli=core()
    original=sys.argv
    try:
        sys.argv=[str(LIB/'git/cli.py'),action,'--wiki-only',*argv]
        return cli.main()
    finally:sys.argv=original


if __name__=='__main__':
    try:sys.exit(main())
    except (ValueError,OSError) as error:
        print('dots git wiki: '+str(error),file=sys.stderr);sys.exit(1)
    except KeyboardInterrupt:sys.exit(130)
