#!/usr/bin/env python3
"""Live visual contracts; all publications and consumers belong to fixtures."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest
from unittest.mock import patch

import test_profile_config as fixtures
from style_config import Styles, current, read, encode
from style_catalog import consumers
from theme_styles import snapshot
from profile_config import context, keys
from config_cli import StylePlan
from config_refresh import refresh, effective, after_save, explain, active, tmux_servers, inline_color
from transactions import Store, digest

ROOT=fixtures.ROOT


class ConfigLive(unittest.TestCase):
    def setUp(self):
        fixtures.ProfileConfig.setUp(self)
        shutil.copytree(ROOT/'default',self.root/'default')
        shutil.copytree(ROOT/'config/gitmux',self.root/'config/gitmux')
        (self.root/'config/tmux').mkdir()
        shutil.copy2(ROOT/'config/tmux/tmux.conf',self.root/'config/tmux/tmux.conf')
        self.env['DOTS_PROFILE']=self.platform
        self.environ=patch.dict(os.environ,self.env,clear=True)
        self.environ.start();self.addCleanup(self.environ.stop)
        current.cache_clear();self.addCleanup(current.cache_clear)
        self.state=Path(self.env['XDG_STATE_HOME'])/'dots'
        self.icon=self.path.parent/'icons.toml'
        self.color=self.path.parent/'colors.toml'
        self.reload=patch('config_refresh.reload_consumers',return_value=[])
        self.mock_reload=self.reload.start();self.addCleanup(self.reload.stop)

    def generation(self):
        gen=self.state/'themes/generations/g.fixture';gen.mkdir(parents=True)
        palette={name:'#aabbcc' for name in ('background','foreground','dark_background','darker_background','lighter_background','light_foreground','dark_foreground','bright_foreground','bright_cyan','bright_green','bright_red','bright_magenta','muted','selection','selection_background','selection_foreground','blue','red','green','yellow','cyan','magenta','accent','error','warning','info','hint','orange')}
        palette['background']='#112233'
        git={name:'#abcdef' for name in ('branch','staged','modified','untracked','conflict','clean','added','deleted','ahead','behind')}
        (gen/'palette.json').write_text(json.dumps(dict(colors=palette)))
        (gen/'preferences.json').write_text(json.dumps(snapshot(palette,self.root)))
        (gen/'colors.json').write_text(json.dumps(dict(schema=1,colors=dict(palette,git=git))))
        for name,text in {'id':'fixture','selection':'fixture','status':'committed','fingerprint':'unchanged-fingerprint',
                          'tmux.conf':'# custom content\nset -g @custom keep\n','fzf.sh':'','gum_env.sh':'',
                          'yazi.toml':'[manager]\nratio=[1,2,3]\n[icon]\nconds=[]\n','opaque':'KEEP'}.items():
            (gen/name).write_text(text+'\n')
        (gen/'yazi').mkdir();(gen/'yazi/flavor.toml').write_text((gen/'yazi.toml').read_text())
        (self.state/'themes/current').write_text(gen.name+'\n')
        (self.state/'current').mkdir();(self.state/'current/theme').symlink_to(gen,target_is_directory=True)
        return gen

    def test_layer_first_alias_and_field_origins(self):
        default=self.root/'default/icons.toml'
        default.write_text(default.read_text()+'\n[apps.cli.applications]\ncodex="default-app"\n')
        self.icon.write_text('[navigation]\ncodex="legacy-profile"\n[applications]\ncodex="profile"\n')
        self.color.write_text('[ui.heading]\nfg="#123456"\nbold=false\n')
        style=Styles(self.root)
        self.assertEqual(style.icon('navigation.codex',app='cli'),'profile')
        self.assertEqual(style.icon('applications.codex',app='tmux'),'profile')
        self.assertFalse(style.style('ui.heading',app='cli')['bold'])
        result=explain('icons.applications.codex',self.root)
        self.assertEqual({row['value'] for row in result['consumers']},{'profile'})
        self.assertTrue(all(row['source']==str(self.icon) for row in result['consumers']))
        self.icon.write_text('[applications]\ncodex=""\n')
        self.assertEqual(Styles(self.root).icon('navigation.codex','fallback',app='cli'),'')

    def test_supported_controls_and_existing_unused_values(self):
        self.color.write_text('[apps.yazi.ui.heading]\nfg="red"\n')
        self.icon.write_text('[unused]\nthing="KEEP"\n')
        self.assertEqual(explain('icons.unused.thing',self.root)['consumers'][0]['refresh'],'unsupported')
        self.assertNotIn('icons.unused.thing',keys(self.root))
        with self.assertRaisesRegex(ValueError,'unsupported'):
            StylePlan(self.root,context(self.root),'icons').edit('unused.thing','EDIT')
        self.assertEqual(explain('colors.apps.yazi.ui.heading.fg',self.root)['consumers'][0]['refresh'],'unsupported')
        self.assertNotIn('colors.apps.yazi.ui.heading.fg',keys(self.root))
        plan=StylePlan(self.root,context(self.root),'colors')
        with self.assertRaisesRegex(ValueError,'unsupported'): plan.edit('apps.yazi.ui.heading.fg','blue')
        plan.edit('apps.yazi.ui.heading.fg',None,unset=True)
        self.assertEqual(consumers('icons','apps.tmux.applications.codex'),['tmux'])
        self.assertIn('colors.todo.status.open.fg',keys(self.root))
        with self.assertRaisesRegex(ValueError,'conflicts'):
            explain('icons.apps.cli.applications.codex',self.root,app='tmux')

    def test_yazi_accent_preserves_other_style_fields(self):
        text='[mgr]\ncwd = { fg = "#aabbcc", bold = true } # retain\nratio = [1, 2, 3]\n[tabs]\nactive = { fg = "#112233", bg = "#445566" }\n'
        updated=inline_color(text,'mgr','cwd','fg','#123456')
        self.assertEqual(updated,text.replace('#aabbcc','#123456'))
        updated=inline_color(updated,'tabs','active','bg','#654321')
        self.assertIn('fg = "#112233", bg = "#654321"',updated)

    def test_publish_preserves_palette_and_unrelated_bytes_and_undo(self):
        old=self.generation();palette=(old/'palette.json').read_bytes()
        self.icon.write_text('[applications]\ncodex="TEST"\n')
        preview=refresh(self.root,dry=True)
        self.assertTrue(preview['publication']);self.assertEqual(active(self.state),old)
        result=refresh(self.root);new=active(self.state)
        self.assertNotEqual(old,new);self.assertEqual((new/'palette.json').read_bytes(),palette)
        self.assertEqual((new/'opaque').read_text(),'KEEP\n')
        self.assertIn('@custom keep',(new/'tmux.conf').read_text())
        self.assertIn('"TEST"',(new/'tmux.visual.conf').read_text())
        self.assertIn('icon\tapplications.codex\tTEST\n',(new/'visual.tsv').read_text())
        self.assertIn('[manager]',(new/'yazi.toml').read_text())
        self.assertEqual(explain('icons.applications.codex',self.root,app='tmux')['consumers'][0]['refresh'],'published')
        repeat=refresh(self.root,retry=False)
        self.assertEqual(repeat['status'],'unchanged');self.assertIsNone(repeat['transaction'])
        store=Store(self.state);ops,guards,catalogs=store.inverse(result['transaction'])
        store.apply('undo',ops,guards,retain=True,catalogs=catalogs)
        self.assertEqual(active(self.state),old)

    def test_only_affected_consumer_and_inactive_save(self):
        self.generation();refresh(self.root)
        before=effective(self.root)
        self.color.write_text('[apps.fzf.ui.border]\nfg="#112244"\n')
        result=after_save(self.root,before)
        self.assertEqual(self.mock_reload.call_args.args[-1],['fzf'])
        self.assertEqual(result['status'],'complete')
        before=effective(self.root)
        inactive='windows' if self.platform!='windows' else 'linux'
        (self.root/'profiles'/inactive/'icons.toml').write_text('[applications]\ncodex="OTHER"\n')
        self.mock_reload.reset_mock()
        self.assertEqual(after_save(self.root,before)['status'],'unchanged')
        self.mock_reload.assert_not_called()

    def test_save_kept_on_publication_or_reload_failure(self):
        old=self.generation();before=effective(self.root)
        self.icon.write_text('[applications]\ncodex="SAVED"\n')
        with patch('config_refresh.render_visual',side_effect=ValueError('fixture failure')):
            result=after_save(self.root,before)
        self.assertEqual(result['status'],'failed');self.assertEqual(active(self.state),old)
        self.assertIn('SAVED',self.icon.read_text())
        self.mock_reload.return_value=[dict(app='tmux',status='failed')]
        result=refresh(self.root)
        self.assertEqual(result['status'],'pending');self.assertNotEqual(active(self.state),old)
        self.assertIn('SAVED',self.icon.read_text())

    def test_stale_inputs_and_unsafe_generated_target_refused(self):
        old=self.generation()
        import config_refresh
        render=config_refresh.render_visual
        def stale(*args):
            render(*args);self.icon.write_text('[applications]\ncodex="RACE"\n')
        with patch('config_refresh.render_visual',side_effect=stale),self.assertRaisesRegex(ValueError,'changed after preview'):
            refresh(self.root)
        self.assertEqual(active(self.state),old)
        outside=self.home/'outside';outside.write_text('KEEP')
        (old/'colors.lua').symlink_to(outside)
        with self.assertRaisesRegex(ValueError,'unsafe generated'):refresh(self.root)
        self.assertEqual(outside.read_text(),'KEEP')

    @unittest.skipUnless(shutil.which('tmux'), 'tmux unavailable')
    def test_private_servers_verified_independently(self):
        import config_refresh
        from menu_sessions import Server
        self.generation()
        self.icon.write_text('[applications]\ncodex="FIX"\n')
        refresh(self.root)
        servers=[]
        for n in range(3):
            socket=str(self.home/('tmux-'+str(n)))
            command=[shutil.which('tmux'),'-S',socket]
            env=dict(self.env,SHELL=shutil.which('bash'))
            subprocess.run(command+['-f','/dev/null','new-session','-d','-s','fixture',shutil.which('sleep')+' 90'],env=env,check=True,capture_output=True)
            self.addCleanup(lambda command=command: subprocess.run(command+['kill-server'],capture_output=True))
            if n==2:
                subprocess.run(command+['set-environment','-g','DOTS',str(self.home/'unrelated')],env=env,check=True)
            servers.append(dict(socket=socket))
        with patch('codex_attention.load',return_value=servers),patch.object(Server,'discover',return_value=None):
            accepted,skipped=tmux_servers(self.root,context(self.root),self.state)
            self.assertEqual(len(accepted),2);self.assertEqual(len(skipped),1)
            self.reload.stop()
            result=config_refresh.reload_consumers(self.root,context(self.root),self.state,active(self.state),['tmux'])
        self.assertEqual([r['status'] for r in result].count('notified'),2)
        for n,server in enumerate(servers):
            value=subprocess.check_output([shutil.which('tmux'),'-S',server['socket'],'show-options','-gqv','@dots-icon-navigation-codex'],env=self.env,text=True).strip()
            self.assertEqual(value,'FIX' if n<2 else '')

    def test_cli_explain_refresh_flags_and_no_refresh(self):
        run=lambda *args,**kw: fixtures.ProfileConfig.run_config(self,*args,**kw)
        before=digest(self.state)
        for native in (False,True):
            data=json.loads(run('explain','icons.applications.codex','--app','cli','--json',native=native).stdout)
            self.assertEqual(data['consumers'][0]['app'],'cli')
            run('refresh','--dry-run','--json',native=native)
        self.assertEqual(before,digest(self.state))
        self.generation()
        before=digest(self.state)
        for native in (False,True):
            preview=json.loads(run('refresh','--dry-run','--json',native=native).stdout)
            self.assertEqual(preview['status'],'preview')
            self.assertIn('tmux',preview['consumers'])
            preview=json.loads(run('set','icons.applications.codex','PREVIEW','--dry-run','--json',native=native).stdout)
            self.assertIn('tmux',preview['refresh']['consumers'])
        self.assertEqual(before,digest(self.state))
        result=json.loads(run('set','icons.applications.codex','TEST','--no-refresh','--json').stdout)
        self.assertNotIn('refresh',result)
        self.assertEqual(run('get','icons.applications.codex',DOTS_COLOR='always').stdout,'TEST\n')

    def test_open_shell_generation_refresh_and_warm_prompt(self):
        old=self.generation()
        (old/'init.zsh').write_text('declare -gA dots_roles foreground background\n'
            'dots_roles[foreground]="#aabbcc"; dots_roles[background]="#112233"\n'
            'dots_roles[accent]="#aabbcc"; dots_roles[muted]="#aabbcc"\n'
            'dots_roles[warning]="#aabbcc"; dots_roles[info]="#aabbcc"\n'
            'THEME=fixture; FLAVOR=""; DOTS_THEME_ID=fixture\n')
        self.icon.write_text('[applications]\ncodex="FIRST"\n')
        refresh(self.root);first=active(self.state)
        self.icon.write_text('[applications]\ncodex="SECOND"\n')
        self.color.write_text('[apps.gum.ui.cursor]\nfg="#123456"\n[apps.fzf.ui.border]\nfg="#654321"\n')
        refresh(self.root);second=active(self.state)
        for shell in ('bash','zsh'):
            if not shutil.which(shell):continue
            with self.subTest(shell=shell):
                pointer=self.state/'current/theme';pointer.unlink();pointer.symlink_to(first)
                flags=['--noprofile','--norc'] if shell=='bash' else ['-df']
                code=r'''
declare -gA dots_options
dots_options[DOTS_INIT_COMPLETION]=0
source "$DOTS/lib/dots/themes/shell.bash"
FZF_DEFAULT_OPTS='--height=40%'
set_theme || exit 10
[[ ${_DOTS_STYLE_ICONS[applications.codex]} == FIRST ]] || exit 11
command ln -sfn "$NEXT" "$_DOTS_THEME_ACTIVE"
false
_dots_theme_precmd
[[ $? == 1 && ${_DOTS_STYLE_ICONS[applications.codex]} == SECOND ]] || exit 12
[[ $GUM_INPUT_CURSOR_FOREGROUND == '#123456' && $FZF_DEFAULT_OPTS == *'border:#654321'* ]] || exit 13
before=$FZF_DEFAULT_OPTS
python3() { printf UNEXPECTED_PYTHON >&2; return 99; }
readlink() { printf UNEXPECTED_READLINK >&2; return 99; }
for n in {1..100}; do _dots_theme_precmd; done
[[ $FZF_DEFAULT_OPTS == "$before" ]] || exit 14
'''
                result=subprocess.run([shutil.which(shell),*flags,'-c',code],env=dict(self.env,NEXT=str(second)),text=True,capture_output=True,timeout=20)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertNotIn('UNEXPECTED_',result.stderr)

    def test_fish_nu_visual_generation_environment(self):
        first=self.generation()
        (first/'shell.tsv').write_text('@theme\tid\tfixture\n@theme\tfamily\tfixture\n@theme\tflavor\tbase\n@palette\tforeground\t#abcdef\n@role\tforeground\t#abcdef\n')
        (first/'visual.tsv').write_text('env\tGUM_INPUT_CURSOR_FOREGROUND\t#112233\nenv\tDOTS_THEME_FZF_COLORS\tborder:#112233\n')
        second=first.with_name('g.next');shutil.copytree(first,second)
        (second/'visual.tsv').write_text('env\tGUM_INPUT_CURSOR_FOREGROUND\t#445566\nenv\tDOTS_THEME_FZF_COLORS\tborder:#445566\n')
        commands={
            'fish': ['--no-config','-i','-c',r'''
source "$DOTS/lib/dots/shell/init.fish"
test "$GUM_INPUT_CURSOR_FOREGROUND" = '#112233'; or exit 11
printf 'g.next\n' > "$_DOTS_STATE/themes/current"
_dots_fish_theme; or exit 12
test "$GUM_INPUT_CURSOR_FOREGROUND" = '#445566'; or exit 13
string match -q '*border:#445566*' -- "$FZF_DEFAULT_OPTS"; or exit 14
set before "$FZF_DEFAULT_OPTS"
_dots_fish_theme
test "$before" = "$FZF_DEFAULT_OPTS"; or exit 15
'''],
            'nu': ['--no-config-file','-i','-c','source '+json.dumps(str(self.root/'lib/dots/shell/init.nu'),ensure_ascii=False)+r'''
if $env.GUM_INPUT_CURSOR_FOREGROUND != '#112233' { exit 11 }
"g.next\n" | save --force ($env.dot.state | path join 'themes/current')
_dots-refresh-theme
if $env.GUM_INPUT_CURSOR_FOREGROUND != '#445566' { exit 13 }
if $env.FZF_DEFAULT_OPTS !~ 'border:#445566' { exit 14 }
let before = $env.FZF_DEFAULT_OPTS
_dots-refresh-theme
if $before != $env.FZF_DEFAULT_OPTS { exit 15 }
''']}
        for shell,args in commands.items():
            if not shutil.which(shell):continue
            with self.subTest(shell=shell):
                (self.state/'themes/current').write_text(first.name+'\n')
                result=subprocess.run([shutil.which(shell),*args],env=dict(self.env,DOTS_INIT_COMPLETION='0'),text=True,capture_output=True,timeout=20)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)


if __name__=='__main__':unittest.main()
