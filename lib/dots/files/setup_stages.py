"""Explicit preparation effects, kept separate from managed publication."""
from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from transactions import Store, digest

THEME_TOOLS = ('bash', 'flock', 'sync', 'sha256sum', 'mktemp', 'awk', 'cat', 'mkdir',
               'mv', 'rm', 'cp', 'ln', 'readlink', 'cmp', 'find', 'sort', 'tee', 'chmod', 'wc')


def verify(guards):
    for path, expected in guards.items():
        if digest(path) != expected: raise ValueError('changed after preview: '+path)


class Preparation:
    def __init__(self, installation, args):
        self.installation, self.args = installation, args
        self.root, self.platform = installation.root, installation.platform
        sys.path.insert(0, str(self.root/'plugins/pkgs'))
        self.packages = dict(schema=1, groups=[])
        if args.package_document is not None:
            from pkgs_lib import manifests
            self.packages = manifests.validate(args.package_document)
            self.package_guard = manifests.guards(args.packages)
            installation.merge_plan([],self.package_guard.expected,label='package inputs')
        self.dependency_document = dict(schema=1, groups=[])
        self.missing = []
        required = []
        theme_adapter = self.root/'lib/dots/themes'/('setup.py' if self.platform == 'windows' else 'setup.bash')
        if 'themes' in args.component and theme_adapter.is_file():
            if sys.version_info < (3, 11): raise ValueError('theme setup needs preinstalled Python 3.11 or newer')
            if self.platform != 'windows': required += list(THEME_TOOLS)
        if 'leaf' in args.component: required += ['git', 'cargo', 'rustc']
        if 'fonts' in args.component and importlib.util.find_spec('fontTools') is None:
            self.missing.append(dict(tool='fontTools', package=None,
                                     reason='install tools/requirements-fonts.txt in the active Python environment explicitly'))
        manager = None
        if any(not shutil.which(t) for t in required):
            from pkgs_lib.detect import default_manager
            try: manager = default_manager()
            except Exception: pass
        packages = {}
        if self.platform == 'termux' and manager == 'apt':
            packages = dict(git='git', cargo='rust', rustc='rust', bash='bash', flock='util-linux',
                            awk='gawk', find='findutils', cmp='diffutils')
            packages.update({t:'coreutils' for t in THEME_TOOLS if t not in packages})
        elif manager in ('apt', 'dnf', 'pacman', 'paru', 'yay', 'xbps'):
            packages = dict(git='git', cargo='cargo' if manager in ('apt','dnf') else 'rust',
                            rustc='rustc' if manager == 'apt' else 'rust', bash='bash',
                            flock='util-linux', awk='gawk', find='findutils', cmp='diffutils')
            packages.update({t:'coreutils' for t in THEME_TOOLS if t not in packages})
        elif manager == 'winget':
            packages = {'git':'Git.Git'}
        for tool in dict.fromkeys(required):
            if not shutil.which(tool):
                self.missing.append(dict(tool=tool, package=packages.get(tool),
                    reason='' if tool in packages else 'install the prerequisite explicitly; no reviewed mapping is available'))
        names = sorted({r['package'] for r in self.missing if r['package']})
        if names:
            self.dependency_document['groups'] = [dict(manager=manager,
                scope='user' if manager == 'winget' else 'system', platforms=[self.platform],
                packages=[dict(name=name) for name in names])]
        self.module = self.platform == 'windows' and bool(names or any(
            g['manager'] == 'winget' and 'windows' in g['platforms'] and any(p['enabled'] for p in g['packages'])
            for g in self.packages['groups']))
        self.leaf = None
        if 'leaf' in args.component:
            from setup_leaf import Build
            self.leaf = Build(installation)
        self.fonts = None
        self.temporary = None
        if 'fonts' in args.component:
            from setup_fonts import Fonts
            self.fonts = Fonts(installation,args)
        self.outcomes = []
        self.results = {}
        self.record = installation.state/'setup-runs'/ (installation.transaction+'.json')

    @property
    def deferred_theme(self):
        return 'themes' in self.args.component and any(r['tool'] in THEME_TOOLS for r in self.missing)

    def close(self):
        if self.temporary is not None:
            self.temporary.cleanup()
            self.temporary = None

    def preview(self):
        rows = []
        if self.missing: rows.append(dict(stage='dependencies', enabled=self.args.with_dependencies, requirements=self.missing))
        if self.module: rows.append(dict(stage='winget-module', enabled=self.args.with_dependencies,
            detail='Use installed Microsoft.WinGet.Client; if missing, explicitly install version 1.29.380 for CurrentUser. No provider or trust changes.'))
        if 'packages' in self.args.component: rows.append(dict(stage='packages', manifest=self.packages))
        for name in ('leaf', 'fonts', 'themes'):
            if name in self.args.component: rows.append(dict(stage=name, status='prepare after approval'))
        if self.fonts:
            next(r for r in rows if r['stage']=='fonts')['selections'] = self.fonts.preview()
        return rows

    def save_outcome(self, stage, status, *, changed=True, **details):
        self.outcomes.append(dict(stage=stage, status=status, **details))
        if not changed and not self.record.exists(): return
        Store(self.installation.state).apply('setup-preparation', [dict(path=str(self.record),
            data=dict(schema=1, root=str(self.root), platform=self.platform, stages=self.outcomes))],
            {str(self.record):digest(self.record)}, retain=True)

    def packages_stage(self, document, label):
        from package_setup import Stage
        stage = Stage(self.root, document=document, json_output=self.args.json)
        if not self.args.json: stage.preview()
        result = stage.apply()
        self.results[label] = result
        self.save_outcome(label, result['status'], result=result,
            changed=result['status'] != 'complete' or any(g['status']=='complete' for g in result['groups']))
        if result['status'] != 'complete':
            raise ValueError(label+' incomplete; completed external changes remain. Record: '+str(self.record))
        return result

    def run(self):
        verify(self.installation.guards)
        if self.missing and (not self.args.with_dependencies or any(not r['package'] for r in self.missing)):
            raise ValueError('missing prerequisites: '+', '.join(r['tool'] for r in self.missing)+
                             '; select --with-dependencies for mapped packages; other prerequisites need explicit installation')
        try:
            if self.module:
                from pkgs_lib.winget import bridge, bridge_command
                capability = bridge('capabilities')
                if capability.get('missing'):
                    if not self.args.with_dependencies: raise ValueError('Microsoft.WinGet.Client is required; select --with-dependencies to approve its current-user installation')
                    from pkgs_lib.common import run
                    run(bridge_command('install-module'))
                    bridge('capabilities')
                    self.save_outcome('winget-module', 'complete')
            if self.dependency_document['groups']:
                self.packages_stage(self.dependency_document, 'dependencies')
                if any(not shutil.which(r['tool']) for r in self.missing):
                    raise ValueError('installed prerequisites are not available to this process; refresh the environment and retry')
            if 'packages' in self.args.component:
                self.packages_stage(self.packages, 'packages')
            if self.leaf:
                result = self.leaf.prepare()
                self.save_outcome('leaf', 'complete', result=result, changed=not result['reused'])
            verify(self.installation.guards)
        except Exception as error:
            self.save_outcome('preparation', 'failed', reason=str(error))
            raise

    def finish(self, installation):
        """Optional payload owners append their final operations here."""
        verify(installation.guards)
        if self.leaf: self.leaf.publish(installation)
        if self.fonts:
            import tempfile
            from transactions import private_directory
            staging = installation.state/'setup-staging'
            private_directory(staging)
            self.temporary = tempfile.TemporaryDirectory(prefix='fonts-',dir=staging)
            self.fonts.installation = installation
            result = self.fonts.prepare(self.temporary.name)
            self.fonts.publish(installation)
            self.save_outcome('fonts','prepared',result=result,changed=bool(result['operations']))
