#!/usr/bin/env python3
"""Deterministic review archives and SHA-256 sums; no Git or publishing side effects."""
import argparse
import gzip
import hashlib
import io
import importlib.util
import json
import re
from pathlib import Path
import tarfile
import zipfile
ROOT = Path(__file__).resolve().parent.parent
version=(ROOT/'VERSION').read_text().strip()
spec=importlib.util.spec_from_file_location('blastoff_packaging_core',ROOT/'lib/blastoff.py')
core=importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)
if core.VERSION != version:
    raise SystemExit('Core VERSION differs from VERSION; update release identities together')
manifest_version = re.search(r"ModuleVersion\s*=\s*'([^']+)'", (ROOT/'powershell/blastoff.psd1').read_text()).group(1)
if manifest_version != version or 'blastoff '+version not in (ROOT/'man/blastoff.1').read_text().splitlines()[0]:
    raise SystemExit('PowerShell/manual release identities differ from VERSION')
# Both public lifecycle frontends and their installed helpers are release payload.
for relative in ('install.ps1','uninstall.ps1','powershell/runtime.ps1',
                 'scripts/powershell_lifecycle.ps1','scripts/powershell_install.py',
                 'lib/argv_transport.py','lib/completion_names.py'):
    if not (ROOT/relative).is_file():
        raise SystemExit('Missing required PowerShell release payload: '+relative)
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output-dir', type=Path, default=ROOT.parent,
                    help='archive destination (use a temporary directory for verification)')
parser.add_argument('--checksums-only', action='store_true')
args=parser.parse_args()
verifier_spec=importlib.util.spec_from_file_location('blastoff_verify',ROOT/'scripts/verify.py')
verifier=importlib.util.module_from_spec(verifier_spec)
verifier_spec.loader.exec_module(verifier)
# Packaging must not rewrite source help according to the host's argparse version.
files=verifier.source_files(ROOT)
manifest={'version':version,'files':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
(ROOT/'CHECKSUMS.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
if args.checksums_only:
    print('Updated CHECKSUMS.json for '+str(len(files))+' source files.')
    raise SystemExit(0)
files.append(ROOT/'CHECKSUMS.json')
files.sort()
output=args.output_dir
output.mkdir(parents=True,exist_ok=True)
executables = {'bin/blastoff', 'scripts/install.sh', 'install.sh', 'uninstall.sh',
               'scripts/build.sh'}
base='blastoff-rebuild-'+version
archive=output/(base+'.zip')
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for p in files:
        info=zipfile.ZipInfo('blastoff-rebuild/'+p.relative_to(ROOT).as_posix(),date_time=(2026,9,30,0,0,0))
        info.compress_type=zipfile.ZIP_DEFLATED
        info.external_attr=((0o100755 if p.relative_to(ROOT).as_posix() in executables else 0o100644)<<16)
        z.writestr(info,p.read_bytes())
archive2=output/(base+'.tar.gz')
with archive2.open('wb') as raw:
    with gzip.GzipFile(fileobj=raw,mode='wb',filename='',mtime=0) as compressed:
        with tarfile.open(fileobj=compressed,mode='w') as tar:
            for p in files:
                info=tarfile.TarInfo('blastoff-rebuild/'+p.relative_to(ROOT).as_posix())
                info.size=p.stat().st_size; info.mtime=0
                info.mode=0o755 if p.relative_to(ROOT).as_posix() in executables else 0o644
                tar.addfile(info,io.BytesIO(p.read_bytes()))
sums=output/(base+'.SHA256SUMS')
sums.write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in [archive,archive2]))
print(archive); print(archive2); print(sums)
