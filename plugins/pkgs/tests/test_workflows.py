"""Package workflow acceptance with owned state and fake managers only."""
import contextlib
import copy
import io
import json
import os
import signal
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

APP = Path(__file__).resolve().parents[1]
ROOT = APP.parents[1]
sys.path.insert(0, str(APP))
from pkgs_lib import cli, policies, workflows, scopes, streams, manifests, go_tools
from pkgs_lib.common import Error, Package, config, budget
from pkgs_lib.backends import Backend


class Workflows(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='pkgs-workflows-')
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.bin = self.home/'bin'; self.bin.mkdir()
        self.env = dict(os.environ, HOME=str(self.home), DOTS=str(ROOT), PREFIX=str(self.home),
                        XDG_CONFIG_HOME=str(self.home/'config'), XDG_STATE_HOME=str(self.home/'state'),
                        XDG_CACHE_HOME=str(self.home/'cache'), XDG_DATA_HOME=str(self.home/'data'),
                        DOTS_COLOR='never', DOTS_ICONS='never', TERM='dumb', VIRTUAL_ENV='',
                        PATH=str(self.bin), TEST_DB=str(self.home/'db.json'), TEST_CALLS=str(self.home/'calls.jsonl'),
                        TERMUX_VERSION='', TERMUX_APP_PACKAGE_MANAGER='', BUNDLE_GEMFILE='')
        self.patcher = patch.dict(os.environ, self.env, clear=True); self.patcher.start()
        self.addCleanup(self.patcher.stop)
        self.cfg = config()
        self.cfg['output'] = 'raw'
        (self.home/'db.json').write_text('{}')
        fake = self.bin/'npm'
        fake.write_text('#!'+sys.executable+'\n'+'''import json,os,sys
from pathlib import Path
args=sys.argv[1:];db=Path(os.environ['TEST_DB']);data=json.loads(db.read_text())
with open(os.environ['TEST_CALLS'],'a') as f:f.write(json.dumps(args)+'\\n')
if args[0]=='ls': print(json.dumps({'dependencies':{k:{'version':v} for k,v in data.items()}}))
elif args[0] in ('install','update'):
    if os.environ.get('TEST_FAIL'):sys.exit(42)
    targets=args[args.index('--')+1:] if '--' in args else []
    for target in targets:
        name,sep,version=target.rpartition('@')
        if not sep or not name:name,version=target,'2.0'
        data[name]=version
    db.write_text(json.dumps(data));print('Installed packages');print('warning: fixture detail',file=sys.stderr)
else:sys.exit(9)
''')
        fake.chmod(0o755)

    def args(self, *words): return cli.parser().parse_intermixed_args(list(words))

    def invoke(self, *words):
        return subprocess.run([sys.executable,'-B',str(APP/'main.py'),*words], capture_output=True,
                              text=True, env=dict(os.environ), timeout=15, start_new_session=True)

    def manifest(self, packages=None):
        return {'schema':1,'groups':[{'manager':'npm','scope':'global',
                'packages':packages if packages is not None else [{'name':'hello'}]}]}

    def test_unattended_upgrade_and_literal_scope(self):
        result = self.invoke('upgrade','--manager','npm','--global','hello')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertNotIn('Proceed?',result.stdout+result.stderr)
        self.assertEqual(json.loads((self.home/'db.json').read_text()),{'hello':'2.0'})
        self.assertEqual(json.loads((self.home/'calls.jsonl').read_text().splitlines()[-1]),['update','--global','--','hello'])

    def test_install_still_needs_approval(self):
        result=self.invoke('install','--manager','npm','hello')
        self.assertEqual(result.returncode,1)
        self.assertIn('No controlling terminal',result.stderr)
        self.assertEqual((self.home/'db.json').read_text(),'{}')

    def test_refresh_without_terminal_or_yes_and_apt_warning(self):
        for name in ('apt', 'apt-cache', 'dpkg-query', 'pkg'):
            path = self.bin/name
            path.write_text('#!'+sys.executable+'\n'+
                'import json,os,sys\n'+
                "open(os.environ['TEST_CALLS'],'a').write(json.dumps(sys.argv)+'\\n')\n"+
                'print('+repr(streams.APT_SCRIPT_WARNING)+',file=sys.stderr)\n'+
                "print('W: Keep this actual warning',file=sys.stderr)\nprint('Hit:1 fixture stable')\n")
            path.chmod(0o755)
        path=self.home/'config/pkgs/config.json';path.parent.mkdir(parents=True)
        path.write_text(json.dumps({'output':'styled'}))
        with patch.dict(os.environ, TERMUX_VERSION='fixture'):
            result=self.invoke('refresh','--manager','apt')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertNotIn('No controlling terminal',result.stderr)
        self.assertNotIn(streams.APT_SCRIPT_WARNING,result.stderr)
        self.assertIn('W: Keep this actual warning',result.stderr)
        self.assertIn('Hit:1 fixture stable',result.stdout)
        calls=[json.loads(line) for line in (self.home/'calls.jsonl').read_text().splitlines()]
        self.assertEqual(len(calls),1);self.assertEqual(calls[0][1:],['update','-y'])
        with patch.dict(os.environ, TERMUX_VERSION='fixture'):
            preview=self.invoke('refresh','--manager','apt','--dry-run')
        self.assertEqual(preview.returncode,0,preview.stderr)
        self.assertIn('Dry run',preview.stdout)
        self.assertEqual(len((self.home/'calls.jsonl').read_text().splitlines()),1)

    def test_apt_warning_split_chunks_and_raw_escape_hatch(self):
        out=io.StringIO();formatter=streams.Formatter(out,dict(self.cfg,_manager='apt'))
        text=streams.APT_SCRIPT_WARNING.encode()
        for chunk in (text[:4],text[4:30],text[30:],b'\nW: real issue\r\n'):
            formatter.feed(chunk);formatter.flush_partial()
        formatter.feed(b'',final=True)
        self.assertEqual(out.getvalue(),'W: real issue\n')
        for text in ('WARNING: apt has another warning', 'WARN', streams.APT_SCRIPT_WARNING+' More context'):
            out=io.StringIO();formatter=streams.Formatter(out,dict(self.cfg,_manager='apt'))
            formatter.feed(text.encode(),final=True)
            self.assertEqual(out.getvalue(),text)
        result=subprocess.run([sys.executable,'-B',str(APP/'main.py'),'format','--manager','apt','--raw'],
            input=(streams.APT_SCRIPT_WARNING+'\n').encode(),capture_output=True,env=dict(os.environ),timeout=10)
        self.assertEqual(result.stdout,(streams.APT_SCRIPT_WARNING+'\n').encode())

    def test_recipe_and_skip_validation(self):
        cfg=copy.deepcopy(self.cfg)
        cfg['policies']={'npm':{'skip':['held'], 'install':{'flags':['--ignore-scripts'],'before':[['echo','{packages}']]},
                       'packages':{'hello':{'install':{'flags':['--save-exact'],'after':[['echo','{package}']]}}}}}
        policies.validate(cfg)
        b=Backend('npm',True)
        p=workflows.plan(b,'install',['hello'],cfg,yes=True)
        self.assertEqual(p.commands,[['echo','hello'],['npm','install','--global','--ignore-scripts','--save-exact','--','hello'],['echo','hello']])
        with self.assertRaisesRegex(Error,'ignore-skip'):workflows.plan(b,'install',['held'],cfg)
        self.assertTrue(workflows.plan(b,'install',['held'],cfg,override=True).commands)
        for commands in ['echo bad', [[None]], [['echo','x{package}']], [['{packages}']]]:
            with self.assertRaises(Error):policies.recipe({'before':commands},True)

    def test_bulk_continues_and_deduplicates(self):
        cfg=copy.deepcopy(self.cfg);cfg['upgrade']['managers']=['pacman','yay','npm']
        with patch('pkgs_lib.scopes.sys.prefix','base'),patch('pkgs_lib.scopes.sys.base_prefix','base'):
            self.assertEqual([m for m,_ in scopes.bulk(cfg)],['pacman','npm'])
        b=Backend('npm',True)
        with patch('pkgs_lib.workflows.scopes.bulk',return_value=[('apt',None),('npm','global')]), \
             patch('pkgs_lib.workflows.available',return_value=True), \
             patch('pkgs_lib.workflows.scopes.make',side_effect=[Error('broken database'),b]), \
             patch.object(b,'installed',return_value=[Package('hello',installed=True)]), \
             patch('pkgs_lib.workflows.apply',return_value=0) as apply, contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(workflows.upgrade(self.args('upgrade'),cfg),1)
            apply.assert_called_once()

    def test_dry_run_runs_no_recipe(self):
        cfg=copy.deepcopy(self.cfg);cfg['policies']={'npm':{'upgrade':{'before':[['touch',str(self.home/'BAD')]]}}}
        with patch('pkgs_lib.workflows.apply',side_effect=AssertionError),contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(workflows.execute(Backend('npm'), 'upgrade',['hello'],self.args('upgrade','--dry-run'),cfg),0)
        self.assertFalse((self.home/'BAD').exists())

    def test_go_inventory_and_fallback(self):
        folder=self.home/'go bin';folder.mkdir();(folder/'tool').write_bytes(b'fake');(folder/'dev').write_bytes(b'fake')
        def metadata(args):
            if args[0]=='env':return json.dumps({'GOBIN':str(folder),'GOPATH':''})
            version='(devel)' if args[-1].endswith('/dev') else 'v1.0.0'
            package='example.org/dev' if args[-1].endswith('/dev') else 'example.org/tool'
            return args[-1]+': go1.25\n\tpath\t'+package+'\n\tmod\t'+package+'\t'+version+'\n'
        with patch.object(go_tools,'local',side_effect=metadata): rows=go_tools.installed()
        self.assertEqual(len(rows),2)
        self.assertTrue(next(p for p in rows if p.details['binary']=='dev').details['disabled_reason'])
        tool=next(p for p in rows if p.details['binary']=='tool')
        with patch.object(go_tools,'which',return_value=None):
            self.assertEqual(go_tools.transactions('upgrade',[tool.name],rows=[tool]),[['go','install','example.org/tool@latest']])
        with patch.object(go_tools,'which',return_value='/fixture/updater'):
            self.assertEqual(go_tools.transactions('upgrade',[tool.name],rows=[tool]),[['go-global-update','tool']])
            self.assertEqual(go_tools.transactions('upgrade',[tool.name],['-trimpath'],[tool]),[['go','install','-trimpath','example.org/tool@latest']])

    def test_pip_evidence_does_not_claim_unknown_ownership(self):
        data={'version':'1','installed':[
            {'metadata':{'name':'ours','version':'1'},'requested':True,'installer':'pip','metadata_location':'/fixture/ours'},
            {'metadata':{'name':'distro','version':'1'},'installer':'rpm','metadata_location':'/fixture/distro'},
            {'metadata':{'name':'source','version':'1'},'installer':'pip','metadata_location':'/fixture/src','direct_url':{'url':'file:///fixture'}}]}
        with patch.object(scopes,'query',return_value=subprocess.CompletedProcess([],0,json.dumps(data),'')), \
             patch.object(scopes,'default_manager',side_effect=Error('none')):
            rows=scopes.pip_rows(Backend('pip'),owned=True)
        self.assertEqual(rows[0][1:],('explicit',''))
        self.assertTrue(rows[1][2]);self.assertTrue(rows[2][2])
        metadata=self.home/'distro.dist-info';metadata.mkdir();(metadata/'METADATA').write_text('Name: distro\n')
        data['installed']=[{'metadata':{'name':'distro','version':'1'},'installer':'pip','metadata_location':str(metadata)}]
        system=Backend('apt')
        with patch.object(scopes,'query',return_value=subprocess.CompletedProcess([],0,json.dumps(data),'')), \
             patch.object(scopes,'default_manager',return_value='apt'),patch.object(scopes,'Backend',return_value=system), \
             patch.object(system,'owners',return_value={str(metadata/'METADATA'):'distro-package'}) as owners:
            rows=scopes.pip_rows(Backend('pip'),owned=True)
        self.assertEqual(list(owners.call_args.args[0]),[str(metadata/'METADATA')]);self.assertIn('system package manager',rows[0][2])

    def test_apt_ownership_batches_exact_paths_and_preserves_unknowns(self):
        paths=[str(self.home/name) for name in ('ours ü','distro','missing','broken','pattern*')]
        result=subprocess.CompletedProcess([],1,'distro:arm64: '+paths[1]+'\n',
            'dpkg-query: no path found matching pattern '+paths[0]+'\n'+
            'dpkg-query: no path found matching pattern '+paths[2]+'\n'+
            'dpkg-query: unexpected database failure\n')
        with patch('pkgs_lib.backends.query',return_value=result) as query:
            owners=Backend('apt').owners(paths+[paths[0]])
        self.assertEqual(query.call_args.args[0],['dpkg-query','-S','--',*paths[:4]])
        self.assertEqual(owners,{paths[0]:'',paths[1]:'distro:arm64',paths[2]:'',paths[3]:None,paths[4]:None})
        with patch('pkgs_lib.backends.query',side_effect=Error('timeout')) as query:
            self.assertEqual(Backend('apt').owners(paths[:2]),dict.fromkeys(paths[:2]))
        self.assertEqual(query.call_count,1)

    def test_pip_export_filters_dependencies_before_batch_ownership(self):
        items=[]
        for index in range(160):
            path=self.home/f'pkg{index}.dist-info';path.mkdir();(path/'METADATA').write_text('fixture')
            items.append(dict(metadata={'name':f'pkg{index}','version':'1'},requested=index<64,
                              installer='pip',metadata_location=str(path)))
        system=Backend('apt')
        evidence={str(Path(item['metadata_location'])/'METADATA'):'' for item in items[:64]}
        with patch.object(scopes,'query',return_value=subprocess.CompletedProcess([],0,json.dumps({'version':'1','installed':items}),'')), \
             patch.object(scopes,'default_manager',return_value='apt'),patch.object(scopes,'Backend',return_value=system), \
             patch.object(system,'owners',return_value=evidence) as owners:
            rows=scopes.pip_rows(Backend('pip'),roots=True,owned=True)
        self.assertEqual(len(rows),64);self.assertTrue(all(not reason for _,_,reason in rows))
        self.assertEqual(set(owners.call_args.args[0]),set(evidence));self.assertEqual(owners.call_count,1)

    def test_export_delayed_stderr_progress_and_timeout_are_bounded(self):
        class Terminal(io.StringIO):
            def isatty(self): return True
        out,err=io.StringIO(),Terminal()
        def slow_inventory(*args,**kwargs):
            time.sleep(.65)
            self.assertIn('Exporting npm (1/1)',err.getvalue())
            self.assertEqual(out.getvalue(),'')
            return [(Package('hello','1'),'explicit','')]
        with contextlib.redirect_stdout(out),contextlib.redirect_stderr(err), \
             patch.object(scopes,'inventory',side_effect=slow_inventory):
            result=manifests.cli(self.args('export','--manager','npm','--global'),dict(self.cfg,output='auto'))
        self.assertEqual(result,0);self.assertEqual(json.loads(out.getvalue())['groups'][0]['packages'][0]['name'],'hello')
        with patch.dict(os.environ,DOTS_PROGRESS='never'),patch.object(manifests,'phase',side_effect=AssertionError('progress disabled')):
            doc,failed=manifests.export(self.args('export','--manager','npm'),dict(self.cfg,output='auto'))
        self.assertFalse(failed)
        out,err=io.StringIO(),Terminal()
        fake=self.bin/'npm';fake.write_text('#!'+sys.executable+'\nimport time\ntime.sleep(10)\n');fake.chmod(0o755)
        start=time.monotonic()
        with budget(.2),contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):
            result=manifests.cli(self.args('export','--manager','npm'),self.cfg)
        self.assertEqual(result,1);self.assertLess(time.monotonic()-start,3)
        self.assertIn('timed out',json.loads(out.getvalue())['notices'][0]['error'])

    def test_help_and_operation_layouts_are_manager_free_and_wrap(self):
        import re
        from pkgs_lib import reports
        from resources import cells
        class Terminal(io.StringIO):
            def isatty(self): return True
        for width in (40,80,120):
            for colors in ('always','never'):
                with patch.dict(os.environ,COLUMNS=str(width),TERM='xterm-256color',NO_COLOR='1'), \
                     patch('pkgs_lib.common.subprocess.Popen',side_effect=AssertionError('manager probe')):
                    outputs=[]
                    for words in ([],['help'],['-h'],['-H'],['refresh','--help']):
                        out=Terminal()
                        with contextlib.redirect_stdout(out):
                            try: code=cli.main([*words,'--color',colors])
                            except SystemExit as error: code=error.code
                        self.assertEqual(code,0);outputs.append(out.getvalue())
                    self.assertTrue(all(text==outputs[0] for text in outputs))
                    text=outputs[0]
                    self.assertIn('Usage',text);self.assertIn('Commands',text);self.assertIn('Options',text)
                    self.assertEqual('\x1b[' in text,colors=='always')
                    self.assertTrue(all(cells(re.sub(r'\x1b\[[0-9;]*m','',line))<=width for line in text.splitlines()))
                    out=Terminal()
                    workflows.display(workflows.Plan(Backend('apt'),'refresh',commands=[['pkg','update','-y']]),
                                      dict(self.cfg,_explicit_color=colors),stream=out)
                    self.assertIn('Refresh repositories',out.getvalue());self.assertIn('Manager',out.getvalue())
        plain=self.invoke('--help')
        self.assertEqual(plain.returncode,0);self.assertTrue(plain.stdout.startswith('usage: pkgs'))
        path=self.home/'config/pkgs/config.json';path.parent.mkdir(parents=True)
        path.write_text(json.dumps({'color':'always'}))
        with patch.dict(os.environ,DOTS_COLOR='auto'),patch('pkgs_lib.common.subprocess.Popen',side_effect=AssertionError('manager probe')):
            os.environ.pop('DOTS_COLOR')
            out=io.StringIO()
            with contextlib.redirect_stdout(out): self.assertEqual(cli.main(['help']),0)
            self.assertIn('\x1b[',out.getvalue())
            out=io.StringIO()
            with contextlib.redirect_stdout(out): self.assertEqual(cli.main(['help','--color','never']),0)
            self.assertTrue(out.getvalue().startswith('usage: pkgs'));self.assertNotIn('\x1b[',out.getvalue())

    def test_export_retains_uv_sources_as_disabled_and_deduplicates_records(self):
        b=Backend('uv-tool')
        with patch.object(b,'installed',return_value=[Package('custom','1')]), \
             patch.object(scopes,'query',return_value=subprocess.CompletedProcess([],0,'custom v1 [required: @ file:///owned/source]\n','')):
            self.assertTrue(scopes.inventory(b,portable=True)[0][2])
        b=Backend('dnf')
        with patch.object(manifests,'available',return_value=True),patch.object(scopes,'make',return_value=b), \
             patch.object(scopes,'inventory',return_value=[(Package('kernel.x86_64','1'),'explicit',''),(Package('kernel.x86_64','2'),'explicit','')]):
            doc,failed=manifests.export(self.args('export','--manager','dnf','--pin-versions'),self.cfg)
        self.assertFalse(failed);packages=doc['groups'][0]['packages']
        self.assertEqual(len(packages),1);self.assertFalse(packages[0]['enabled']);self.assertIsNone(packages[0]['pin'])

    def test_manifest_read_does_not_probe_managers(self):
        path=self.home/'-manifest ü.json';path.write_text(json.dumps(self.manifest()))
        with patch.object(manifests,'available',side_effect=AssertionError):
            out=io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(manifests.cli(self.args('manifest',str(path),'--json'),self.cfg),0)
            self.assertEqual(json.loads(out.getvalue())['groups'][0]['packages'][0]['name'],'hello')
        result=self.invoke('manifest',str(path),'--json')
        self.assertEqual(result.returncode,0,result.stderr)

    def test_update_manifest_preserves_edits_adds_packages_and_is_repeat_safe(self):
        path=self.home/'-packages ü.json'
        previous=self.manifest([
            {'name':'hello','observed_version':'1','pin':'0.5','selection':'manual'},
            {'name':'disabled','enabled':False,'reason':'keep disabled','pin':'1'},
            {'name':'wanted-later','pin':'3','observed_version':'2'}])
        path.write_text(json.dumps(previous));original=path.read_bytes()
        (self.home/'db.json').write_text(json.dumps({'hello':'2','disabled':'4','new':'5'}))
        words=['export','--update','--manager','npm','--global','--output',str(path)]
        preview=self.invoke(*words,'--dry-run','--color','always')
        self.assertEqual(preview.returncode,0,preview.stderr);self.assertEqual(path.read_bytes(),original)
        proposed=json.loads(preview.stdout);rows={p['name']:p for p in proposed['groups'][0]['packages']}
        self.assertEqual(rows['hello']['observed_version'],'2');self.assertEqual(rows['hello']['pin'],'0.5')
        self.assertEqual(rows['hello']['selection'],'manual')
        self.assertFalse(rows['disabled']['enabled']);self.assertEqual(rows['disabled']['reason'],'keep disabled')
        self.assertEqual(rows['wanted-later']['pin'],'3');self.assertEqual(rows['wanted-later']['observed_version'],'2')
        self.assertEqual(rows['new']['observed_version'],'5')
        saved=self.invoke(*words,'--yes');self.assertEqual(saved.returncode,0,saved.stderr)
        self.assertEqual(json.loads(path.read_text()),proposed)
        before=path.stat().st_mtime_ns
        saved=self.invoke(*words,'--yes');self.assertEqual(saved.returncode,0,saved.stderr)
        self.assertEqual(path.stat().st_mtime_ns,before)

    def test_update_default_uses_leaf_profile_and_refuses_stale_or_partial_snapshots(self):
        dots=self.home/'checkout';leaf=dots/'profiles/linux/distros/debian';leaf.mkdir(parents=True)
        (dots/'profiles/linux/profile.json').write_text(json.dumps({'schema':1,'id':'linux'}))
        (leaf/'profile.json').write_text(json.dumps({'schema':1,'id':'linux/debian','extends':['linux']}))
        facts={'platform':'linux','distro':'debian','family':[]}
        manifests.dotslib()
        with patch('profiles.detect',return_value=facts):
            path=manifests.default_path(dots);self.assertEqual(path,leaf/'packages.json')
            args=self.args('export','--update','--manager','npm','--global','--yes')
            with patch.dict(os.environ,DOTS=str(dots)),contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(manifests.cli(args,self.cfg),0)
            self.assertTrue(path.exists());self.assertFalse((dots/'packages.json').exists())
            snapshot=manifests.Update(path,args,self.cfg,root=dots,profile_default=True)
            path.write_text(json.dumps(self.manifest([{'name':'edited'}])))
            before=path.read_bytes()
            with self.assertRaisesRegex(Error,'changed after preview'):snapshot.save(args)
            self.assertEqual(path.read_bytes(),before)
            with patch.object(manifests,'export',return_value=({'schema':1,'groups':[],'notices':[{'error':'fixture failure'}]},True)):
                with self.assertRaisesRegex(Error,'incomplete'):manifests.Update(path,args,self.cfg)
            self.assertEqual(path.read_bytes(),before)
        with patch('profile_config.context',return_value={'layers':[]}):
            with self.assertRaisesRegex(ValueError,'No active'):manifests.default_path(dots)

    def test_merge_retains_foreign_groups_and_existing_manager_identity(self):
        old={'schema':1,'groups':[{'manager':'pacman','scope':'system','platforms':['termux'],
            'packages':[{'name':'editor','pin':None,'observed_version':'1','enabled':False,'reason':'held'}]}]}
        fresh={'schema':1,'groups':[{'manager':'yay','scope':'system','platforms':['termux'],
            'packages':[{'name':'editor','observed_version':'2'},{'name':'new'}]}]}
        with patch.object(manifests,'platform',return_value='termux'):
            merged=manifests.merge(old,fresh)
        self.assertEqual(merged['groups'][0]['manager'],'pacman')
        self.assertEqual(merged['groups'][0]['packages'][0]['observed_version'],'2')
        self.assertFalse(merged['groups'][0]['packages'][0]['enabled'])
        with patch.object(manifests,'platform',return_value='linux'):
            self.assertEqual(manifests.merge(old,fresh),manifests.validate(old))

    def test_restore_pins_and_repeat_noop(self):
        path=self.home/'packages.json';path.write_text(json.dumps(self.manifest([{'name':'hello','pin':'1.2'}])))
        before=self.invoke('restore',str(path),'--dry-run','--json')
        self.assertEqual(before.returncode,0,before.stderr)
        self.assertEqual((self.home/'db.json').read_text(),'{}')
        result=self.invoke('restore',str(path),'--yes','--json')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout)['status'],'complete')
        self.assertEqual(json.loads((self.home/'db.json').read_text()),{'hello':'1.2'})
        again=self.invoke('restore',str(path),'--yes','--json')
        self.assertEqual(json.loads(again.stdout)['groups'][0]['status'],'unchanged')
        calls=[json.loads(s) for s in (self.home/'calls.jsonl').read_text().splitlines()]
        self.assertEqual(sum(c[0]=='install' for c in calls),1)

    def test_restore_keeps_existing_unpinned_and_skips_disabled(self):
        (self.home/'db.json').write_text('{"hello":"0.1"}')
        doc=manifests.validate(self.manifest([{'name':'hello'},{'name':'skip','enabled':False}]))
        entries=manifests.prepare(doc,self.cfg)
        self.assertEqual(entries[0]['plan'].commands,[])
        self.assertEqual(entries[0]['plan'].skipped[0]['package'],'skip')

    def test_manifest_rejects_commands_duplicates_and_unsupported_pins(self):
        for doc in [dict(self.manifest(), commands=[['bad']]), self.manifest([{'name':'x;id'}]),
                    self.manifest([{'name':'x'},{'name':'x'}]),
                    {'schema':1,'groups':[{'manager':'pacman','scope':'system','packages':[{'name':'x','pin':'1'}]}]}]:
            with self.assertRaises(Error):manifests.validate(doc)

    def test_prerequisite_rediscovery_after_system(self):
        doc=manifests.validate({'schema':1,'groups':[{'manager':'npm','scope':'global','packages':[]},
                    {'manager':'apt','scope':'system','packages':[]}]})
        system=Backend('apt');language=Backend('npm',True)
        order=[]
        def prepare(group,cfg,ignore=False):
            order.append(group['manager'])
            b=system if group['manager']=='apt' else language
            return dict(group=group,status='planned',reason='',plan=workflows.Plan(b,'install'))
        with patch.object(manifests,'prepare_group',side_effect=prepare):
            result=manifests.apply(doc,self.cfg)
        self.assertEqual(order,['apt','npm']);self.assertEqual(result['status'],'complete')

    def test_missing_manager_partial_failure(self):
        doc=manifests.validate(self.manifest())
        with patch.object(manifests,'available',return_value=False):result=manifests.apply(doc,self.cfg)
        self.assertEqual(result['status'],'incomplete')

    def test_disabled_groups_and_coexisting_gem_pin_are_noops(self):
        document=manifests.validate(self.manifest([{'name':'source','enabled':False}]))
        with patch.object(manifests,'available',side_effect=AssertionError):
            self.assertEqual(manifests.prepare(document,self.cfg)[0]['status'],'skipped')
        group=manifests.validate({'schema':1,'groups':[{'manager':'gem','scope':'active','packages':[{'name':'rake','pin':'13.1'}]}]})['groups'][0]
        b=Backend('gem')
        with patch.object(manifests,'available',return_value=True),patch.object(scopes,'make',return_value=b), \
             patch('pkgs_lib.backends.run',return_value='rake (13.2, 13.1)\n'):
            self.assertEqual(manifests.prepare_group(group,self.cfg)['plan'].commands,[])

    def test_export_overwrite_retains_undo_and_rolls_back_failure(self):
        path=self.home/'saved.json';path.write_text('original\n')
        args=self.args('export','--output',str(path),'--yes');manifests.dotslib()
        from files.transactions import Store
        from files.file_platform import state_root
        manifests.write_export(path,self.manifest(),args)
        store=Store(state_root());record=store.records()[-1]
        operations,guards,catalogs=store.inverse(record['id'])
        store.apply('undo',operations,guards,retain=True,catalogs=catalogs)
        self.assertEqual(path.read_text(),'original\n')
        # Existing Store rollback is exercised through this export boundary.
        from files import transactions
        with patch.object(transactions,'prepare_text',side_effect=OSError('fixture write failure')):
            with self.assertRaises(OSError):manifests.write_export(path,self.manifest(),args)
        self.assertEqual(path.read_text(),'original\n')

    def test_failed_inventory_does_not_hide_independent_restore_groups(self):
        doc=self.manifest();doc['groups'].append({'manager':'gem','scope':'user','packages':[]})
        with patch.object(manifests,'prepare_group',side_effect=[Error('broken inventory'),dict(group=doc['groups'][1],status='planned',reason='',plan=None)]):
            entries=manifests.prepare(doc,self.cfg)
        self.assertEqual([e['status'] for e in entries],['failed','planned'])

    def test_system_overrides_keep_arch_full_upgrade_and_dnf_pin_shape(self):
        cfg=copy.deepcopy(self.cfg);cfg['policies']={'pacman':{'skip':['held'],'packages':{'custom':{'upgrade':{'replace':[['custom-update']]}}}}}
        b=Backend('pacman');b.termux=False
        with patch.object(b,'installed',return_value=[Package(n) for n in ('ordinary','held','custom')]),patch('os.geteuid',return_value=0):
            commands=workflows.plan(b,'upgrade',[],cfg,bulk=True).commands
        self.assertIn('-Syu',commands[0]);self.assertIn('held,custom',commands[0]);self.assertEqual(commands[1],['custom-update'])
        b=Backend('dnf');b.pins={'hello.x86_64':'1.2-3'}
        self.assertIn('hello-1.2-3.x86_64',policies.commands(b,'install',['hello.x86_64'],self.cfg,True)[0])

    def test_raw_formatter_preserves_bytes_and_interruption_stops_child(self):
        raw=b'\x1b[31munknown\r\xff\n'
        p=subprocess.run([sys.executable,'-B',str(APP/'main.py'),'format','--raw'],input=raw,capture_output=True,env=dict(os.environ))
        self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(p.stdout,raw)
        pidfile=self.home/'child.pid'
        child='import os,time,signal;from pathlib import Path;signal.signal(signal.SIGINT,signal.SIG_IGN);Path('+repr(str(pidfile))+').write_text(str(os.getpid()));time.sleep(60)'
        driver='import sys;sys.path.insert(0,'+repr(str(APP))+');from pkgs_lib.streams import run;run([sys.executable,"-c",'+repr(child)+'],{"output":"styled"})'
        process=subprocess.Popen([sys.executable,'-B','-c',driver],stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
        try:
            deadline=time.monotonic()+5
            while not pidfile.exists() and time.monotonic()<deadline:time.sleep(.02)
            self.assertTrue(pidfile.exists())
            process.send_signal(signal.SIGINT);process.communicate(timeout=5)
            with self.assertRaises(ProcessLookupError):os.kill(int(pidfile.read_text()),0)
        finally:
            if process.poll() is None:process.kill();process.communicate()

    def test_export_store_idempotence_and_stale_guards(self):
        path=self.home/'-export ü.json';args=self.args('export','--output',str(path),'--yes')
        manifests.write_export(path,self.manifest(),args)
        before=path.stat().st_mtime_ns
        manifests.write_export(path,self.manifest(),args)
        self.assertEqual(path.stat().st_mtime_ns,before)
        check=manifests.guards(path);path.write_text('{}')
        with self.assertRaisesRegex(Error,'changed after preview'):check()
        link=self.home/'broken';link.symlink_to(self.home/'absent')
        with self.assertRaises(Error):manifests.write_export(link,self.manifest(),args)

    def test_native_config_guard_reset_and_consumer(self):
        manifests.dotslib()
        from config_pkgs import NativePlan, Native
        plan=NativePlan(ROOT,None);plan.edit('apps.pkgs.output','raw');plan.apply('set')
        self.assertEqual(config()['output'],'raw')
        pending=NativePlan(ROOT,None);pending.edit('apps.pkgs.output','styled')
        native=Native(ROOT);document=json.loads(native.path.read_text());document['unrelated']='preserved'
        native.path.write_text(json.dumps(document))
        with self.assertRaises(ValueError):pending.apply('set')
        plan=NativePlan(ROOT,None);plan.edit('apps.pkgs.output',unset=True);plan.apply('unset')
        self.assertEqual(config()['output'],'auto');self.assertEqual(config()['unrelated'],'preserved')

    def test_stream_fragments_controls_and_full_unknown_text(self):
        out=io.StringIO();formatter=streams.Formatter(out,{'output':'styled','color':'never'})
        formatter.feed(b'\x1b[3');formatter.feed(b'1merror: bad\x1b[0m\r  unknown ')
        formatter.flush_partial();formatter.feed(b'text\nProceed? ');formatter.flush_partial();formatter.feed(b'',final=True)
        self.assertEqual(out.getvalue(),'error: bad\n  unknown text\nProceed? ')
        out=io.StringIO();formatter=streams.Formatter(out,{'color':'never'})
        formatter.feed('界\r'.encode());formatter.feed(b'\nnext\r\n',final=True)
        self.assertEqual(out.getvalue(),'界\nnext\n')

    def test_stream_color_plain_and_no_color_preserve_unknown_content(self):
        class Terminal(io.StringIO):
            def isatty(self):return True
        for width in (40,80,120):
            for mode,no_color,painted in [('always','',True),('auto','1',False),('never','',False)]:
                with patch.dict(os.environ,COLUMNS=str(width),TERM='xterm',NO_COLOR=no_color,DOTS_ICONS='always'):
                    out=Terminal();formatter=streams.Formatter(out,{'output':'styled','_explicit_color':mode})
                    formatter.feed(b'error: example\n  unknown unchanged\n',final=True)
                    self.assertEqual('\x1b[' in out.getvalue(),painted)
                    self.assertIn('  unknown unchanged\n',out.getvalue())
                    self.assertNotIn('None',out.getvalue())

    def test_real_stream_runner_preserves_status_and_both_streams(self):
        code='import os,time;os.write(1,b"prompt: ");time.sleep(.2);os.write(2,b"warning: detail\\n");os.write(1,b"unknown\\n");raise SystemExit(17)'
        out,err=io.StringIO(),io.StringIO()
        with contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):
            rc=streams.run([sys.executable,'-c',code],{'output':'styled','color':'never'})
        self.assertEqual(rc,17);self.assertIn('prompt: unknown',out.getvalue());self.assertIn('warning: detail',err.getvalue())

    def test_narrow_plain_reports_keep_full_identities(self):
        from pkgs_lib.reports import report
        class Terminal(io.StringIO):
            def isatty(self):return True
        for width in (40,80,120):
            with patch.dict(os.environ,COLUMNS=str(width),TERM='xterm'):
                out=Terminal();item=workflows.Plan(Backend('npm',True),'upgrade',['@scope/a-long-package'],[['npm','update','--','@scope/a-long-package']])
                workflows.display(item,{'color':'never'},stream=out)
                self.assertIn('@scope/a-long-package',out.getvalue().replace('\n',''))


if __name__=='__main__':unittest.main()
