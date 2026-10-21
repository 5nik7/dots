"""Measure copied profiles, never the developer's actual startup files.

One initial sample and ten warm fresh-process samples; redirected input means
the baseline excludes PSReadLine. --starship includes its module setup and an
optional copied integration; job discovery is stubbed. No keyboard/desktop rendering.
"""
import argparse
import os
from pathlib import Path
import shutil
import json
import statistics
import subprocess
import time

from test_powershell_init import PowerShellInitTests, PWSH, literal


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--starship', action='store_true', help='Also measure installed Starship with a synthetic config')
    parser.add_argument('--integration', type=Path, help='Copy an inspected terminal integration into the fixture')
    args = parser.parse_args()
    if not PWSH:
        raise SystemExit('PowerShell unavailable')
    fixture = PowerShellInitTests()
    fixture.setUp()
    try:
        entry = literal(fixture.repo / 'shells/powershell/profile.ps1')
        rows = {}
        modes = ['no_profile', 'lean']
        native_path = fixture.env['PATH']
        if args.starship:
            starship = shutil.which('starship')
            if not starship:
                raise SystemExit('Starship unavailable')
            fixture.env['PSModulePath'] += os.pathsep + str(Path(PWSH).parent / 'Modules')
            if os.name == 'nt':
                fixture.env['PSModulePath'] += os.pathsep + str(Path(os.environ['ProgramFiles']) / 'WindowsPowerShell/Modules')
            config = fixture.home / 'starship.toml'
            config.write_text("format = 'fixture $character'\nadd_newline = false\n[character]\nsuccess_symbol = '>'\nerror_symbol = '!'\n")
            fixture.env['STARSHIP_CONFIG'] = str(config)
            fixture.env['STARSHIP_CACHE'] = str(fixture.home / 'starship-cache')
            modes.append('starship')
        integration = fixture.home / 'Documents/shell-integration_v7.ps1'
        for mode in modes:
            fixture.env['PATH'] = native_path
            if mode == 'starship':
                fixture.env['PATH'] += os.pathsep + str(Path(starship).parent)
                if args.integration:
                    integration.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(args.integration, integration)
            samples = []
            for _ in range(11):
                body = f'. {entry}; ' if mode != 'no_profile' else ''
                code = ("$PROFILE.CurrentUserAllHosts=" + literal(fixture.home / "Documents" / "profile.ps1") + "; " +
                        "function global:Get-Job { }; $ErrorActionPreference='Stop'; try { "
                        "$timer=[Diagnostics.Stopwatch]::StartNew(); " + body +
                        "$loaded=$timer.Elapsed.TotalMilliseconds; $rendered=prompt; "
                        "@{profile_ms=$loaded; first_prompt_ms=$timer.Elapsed.TotalMilliseconds; "
                        "version=$PSVersionTable.PSVersion.ToString(); rendered=$rendered; "
                        "starship=[bool]($global:_DotsOptionalFeatures -and $global:_DotsOptionalFeatures['starship']); "
                        "integration=[bool]$global:__ShellInteg_Installed} | ConvertTo-Json -Compress; "
                        "exit 0 } catch { [Console]::Error.WriteLine($_); exit 1 }")
                started = time.perf_counter()
                result = subprocess.run([PWSH, '-NoProfile', '-NoLogo', '-NoExit', '-Command', code],
                    cwd=fixture.home, env=fixture.env, input='', capture_output=True,
                    text=True, timeout=30)
                wall = (time.perf_counter() - started) * 1000
                if result.returncode or result.stderr:
                    raise RuntimeError(result.stderr)
                sample = json.loads(result.stdout)
                if mode == 'starship' and (not sample['starship'] or sample['rendered'].count('fixture ') != 1):
                    raise RuntimeError('Starship did not render the synthetic prompt exactly once')
                sample['process_ms'] = wall
                samples.append(sample)
            rows[mode] = {'initial': samples[0], 'warm': {
                key: {'median': round(statistics.median(s[key] for s in samples[1:]), 2),
                      'max': round(max(s[key] for s in samples[1:]), 2)}
                for key in ('profile_ms', 'first_prompt_ms', 'process_ms')}}
        print(json.dumps(rows, indent=2))
    finally:
        fixture.doCleanups()


if __name__ == '__main__':
    main()
