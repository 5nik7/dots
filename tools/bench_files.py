#!/usr/bin/env python3
"""Advisory file-catalog scaling measurements in disposable roots."""
import argparse
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import tempfile
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--samples', type=int, default=5)
    args = parser.parse_args()
    if args.samples < 1:
        parser.error('samples must be positive')
    backend = Path(__file__).resolve().parents[1] / 'lib/dots/files/catalog.py'
    root = Path(tempfile.mkdtemp(prefix='dots-files-bench-'))
    home = root / 'home space ü'
    repo = root / 'repo'
    (repo / '.dots').mkdir(parents=True)
    home.mkdir()
    (repo / 'config/app').mkdir(parents=True)
    (repo / '.dots/sources.json').write_text(json.dumps(dict(schema=1, sources=[dict(id='dots', path='.', roots=['config'], platforms=['linux'])])))
    env = dict(HOME=str(home), DOTS=str(repo), XDG_CONFIG_HOME=str(home / 'config'), PATH=os.environ['PATH'])
    if os.environ.get('LD_PRELOAD'):
        env['LD_PRELOAD'] = os.environ['LD_PRELOAD']
    results = dict(platform='native Termux' if 'com.termux/' in sys.executable else 'native ' + os.uname().sysname, catalog_platform='linux', samples=args.samples, counts={})
    for count in (100, 1000, 10000):
        rows = [dict(id=f'item-{i}', source='config/app', app='app', category='config', platforms=['linux'], target='${CONFIG}/app-'+str(i), strategy='directory-link') for i in range(count)]
        (repo / '.dots/files.json').write_text(json.dumps(dict(schema=1, repository='dots', resources=rows)))
        values = []
        for i in range(args.samples + 1):
            start = time.perf_counter()
            proc = subprocess.run([sys.executable, '-B', str(backend), 'list', '--platform', 'linux', '--json'], env=env, cwd=home, capture_output=True, check=True, timeout=60)
            elapsed = time.perf_counter() - start
            assert len(json.loads(proc.stdout)['resources']) == count
            if i:
                values.append(elapsed)
        assert not (repo / '.dots/files.lock').exists()
        results['counts'][str(count)] = dict(median_ms=statistics.median(values)*1000, samples_seconds=values)
    (root / 'results.json').write_text(json.dumps(results, indent=2)+'\n')
    print(root / 'results.json')
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
