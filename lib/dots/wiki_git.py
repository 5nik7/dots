"""Wiki association hooks for existing Git workflow and inspection controllers."""
import os
from pathlib import Path
import sys

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


def association(base):
    if not (base/MANIFEST).is_file(): return None
    spec=manifest(Reader(base));path=checkout(base,spec)
    if not path.exists():return dict(path=str(path),kind='wiki',availability='missing',reason='use dots wiki init')
    require_checkout(path)
    return dict(path=str(path),kind='wiki',availability='available',reason='')


class Companion:
    def __init__(self,workflow):
        self.workflow=workflow;self.source=workflow.root
        self.only=getattr(workflow.args,'wiki_only',False)
        self.row=association(self.source)
        if self.only and (not self.row or self.row['availability']!='available'):
            raise ValueError('wiki checkout unavailable; use dots wiki init')
        self.path=Path(self.row['path']) if self.row else None
        self.snapshot=None
        self.definition=sha(Reader(self.source).read(MANIFEST)) if self.row else None
        if self.only:workflow.root=self.path

    def recheck(self):
        current=association(self.source)
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
        import argparse
        import inspection
        p=argparse.ArgumentParser(add_help=False);p.add_argument('-C','--directory',default=os.environ.get('DOTS',str(LIB.parents[1])))
        args,rest=p.parse_known_args(argv)
        base=inspection.context(args.directory);row=association(base)
        if not row or row['availability']!='available':raise ValueError('wiki checkout unavailable; use dots wiki init')
        return inspection.main(['info','-C',row['path'],'--no-wiki',*rest])
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
