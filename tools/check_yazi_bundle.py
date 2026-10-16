#!/usr/bin/env python3
"""Read-only consistency check between standalone and bundled runtime sources."""
import argparse
from pathlib import Path
import sys
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);args=p.parse_args()
bundle=Path(__file__).resolve().parents[1]/'config/yazi/plugins/dots.yazi'
names={x.name for x in args.source.glob('*.lua') if not x.name.startswith('test')}
names|={x.name for x in bundle.glob('*.lua') if not x.name.startswith('test')}
failed=[]
for name in sorted(names):
 a,b=args.source/name,bundle/name
 if not a.is_file() or not b.is_file() or a.read_bytes()!=b.read_bytes():failed.append(name)
if failed: print('Runtime copies differ: '+', '.join(failed),file=sys.stderr);sys.exit(1)
print(f'Runtime copies match ({len(names)} Lua modules).')
