#!/usr/bin/env python3
"""Actual shell completion insertion and native adapter checks in owned roots."""
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import unittest

from test_menus import MenuFixture, ROOT

PLUGIN = Path(os.environ.get('DOTS_TEST_FZF_TAB') or Path.home()/'.local/share/zinit/plugins/Aloxaf---fzf-tab')
ENGINE = os.environ.get('DOTS_TEST_POWERSHELL')


class TodoShells(MenuFixture):
    def setUp(self):
        super().setUp()
        self.repo = Path(self.env['DOTS'])
        shutil.copytree(ROOT/'lib/dots', self.repo/'lib/dots', ignore=shutil.ignore_patterns('__pycache__'))
        (self.repo/'bin').mkdir()
        for name in ['dots','dots.ps1','todo','todo.ps1',*[p.name for p in (ROOT/'bin').glob('dots-todo*')]]:
            shutil.copy2(ROOT/'bin'/name,self.repo/'bin'/name)
        self.env['PATH'] = str(self.repo/'bin')+os.pathsep+self.env['PATH']
        os.environ['PATH'] = self.env['PATH']
        from todo_core import Goals, scope
        self.goal = Goals(scope()).mutate('add',title='Completion café',alias='dots-goal',tags=['unique-tag'])['goals'][0]
        # The standalone command runs outside Dots: explicitly register the owned home.
        config=self.home/'config/dots';config.mkdir(parents=True,exist_ok=True)
        (config/'projects.json').write_text(json.dumps(dict(schema=1,projects=[str(self.home)])))
        self.other = Goals(scope(standalone=True,project=self.home)).mutate('add',title='Other project',alias='project-goal') ['goals'][0]

    @unittest.skipIf(os.name=='nt','POSIX interactive shell acceptance')
    def test_real_tab_bash_zsh_fish_and_scope(self):
        from bash_dots_pty import Terminal
        for shell in ('bash','zsh','fish'):
            executable=shutil.which(shell)
            if not executable: continue
            with self.subTest(shell=shell):
                term=Terminal(executable,self.env,self.home)
                try:
                    init='autoload -Uz compinit; compinit -D; ' if shell=='zsh' else ''
                    term.send(init+'source "$DOTS/lib/dots/completion/'+shell+'"; printf "INITIALIZED\\n"\r')
                    term.wait(b'INITIALIZED\r\n')
                    for prefix,goal in [('dots todo',self.goal),('todo',self.other)]:
                        term.send(prefix+' show '+goal['id'][:7]+'\t')
                        term.wait(goal['id'][7:].encode())
                        term.send(' --json\r')
                        term.wait(b'"goals":')
                        term.send(prefix+' note '+goal['alias'][:3]+'\t')
                        term.wait(goal['alias'][3:].encode())
                        term.send(' "Appended from '+shell+'" --json\r')
                        term.wait(b'"action": "note"')
                        project_tag=goal['tags'][-1]
                        term.send(prefix+' list --tag '+project_tag[:2]+'\t')
                        term.wait(project_tag[2:].encode())
                        term.send(' --json\r')
                        term.wait(b'"tags":')
                    term.send('todo list --priority h\t')
                    term.wait(b'high')
                    term.send('\x03')
                finally:term.close()

    @unittest.skipIf(os.name=='nt','POSIX Zsh/FZF-tab acceptance')
    def test_zsh_fzf_tab_goal_description_and_insertion(self):
        if not shutil.which('zsh') or not shutil.which('fzf') or not (PLUGIN/'fzf-tab.plugin.zsh').is_file():
            self.skipTest('Zsh/FZF-tab source unavailable')
        from bash_dots_pty import Terminal
        plugin=self.base/'fzf-tab'
        shutil.copytree(PLUGIN,plugin,ignore=shutil.ignore_patterns('.git'))
        from todo_core import Goals, scope
        Goals(scope()).mutate('add',title='Second completion goal')
        term=Terminal(shutil.which('zsh'),self.env,self.home)
        try:
            term.send('autoload -Uz compinit; compinit -D; source "$DOTS/lib/dots/completion/zsh"; source '+
                shlex.quote(str(plugin/'fzf-tab.plugin.zsh'))+'; printf "INITIALIZED\\n"\r')
            term.wait(b'INITIALIZED\r\n')
            term.send('dots todo show \t')
            term.wait(b'Completion')
            term.send('Completion\r')
            term.wait(self.goal['alias'].encode())
            term.send(' --json\r')
            term.wait(b'"goals":')
        finally:term.close()

    def test_native_powershell_entry_and_completion(self):
        engines=[ENGINE] if ENGINE else [name for name in ('powershell','pwsh') if shutil.which(name)]
        if not engines:self.skipTest('native PowerShell engine unavailable')
        for engine in engines:
            if not shutil.which(engine):self.fail('requested PowerShell engine unavailable: '+engine)
            script=self.base/'check.ps1'
            script.write_text('''$ErrorActionPreference = 'Stop'
. (Join-Path $env:DOTS 'lib/dots/completion/powershell')
$line = 'todo show '
$result = [System.Management.Automation.CommandCompletion]::CompleteInput($line, $line.Length, $null)
$result.CompletionMatches | ForEach-Object { $_.CompletionText }
& (Join-Path $env:DOTS 'bin/todo.ps1') show $env:TODO_TEST_ID --json
''')
            env=dict(self.env,TODO_TEST_ID=self.other['alias'],PSModuleAnalysisCachePath=str(self.home/'ps-cache'),
                     POWERSHELL_TELEMETRY_OPTOUT='1',POWERSHELL_UPDATECHECK='Off')
            result=subprocess.run([engine,'-NoLogo','-NoProfile','-File',str(script)],cwd=self.home,env=env,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertGreaterEqual(result.stdout.count(self.other['alias']),2,result.stdout)
            self.assertIn(self.other['id'],result.stdout)
            self.assertNotIn(self.goal['id'],result.stdout)


if __name__=='__main__':unittest.main()
