#!/usr/bin/env python3
"""Compare public shell interfaces against a retained source snapshot."""
import argparse
import json
from pathlib import Path
from zsh_fixture import REPO, fixture, run

CODE = r'''
print -r -- __STATE__
for key in ${(ok)aliases}; do print -r -- "alias:$key=${aliases[$key]}"; done
for key in ${(ok)_comps}; do print -r -- "completion:$key=${_comps[$key]}"; done
for key in ${(ok)functions}; do print -r -- "function:$key"; done
print -r -- __END_STATE__
'''


def snapshot(source):
    root, repo, env = fixture(source)
    p = run(env, CODE)
    if p.returncode:
        raise RuntimeError(p.stderr)
    text = p.stdout.split('__STATE__\n', 1)[1].split('__END_STATE__', 1)[0]
    text = text.replace(str(root), '<fixture>')
    data = set(text.splitlines())
    (root / 'public-state.txt').write_text('\n'.join(sorted(data)))
    return root, data


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('baseline', type=Path)
    parser.add_argument('--source', type=Path, default=REPO)
    args = parser.parse_args()
    before_root, before = snapshot(args.baseline.resolve())
    after_root, after = snapshot(args.source.resolve())
    result = {'before_fixture': str(before_root), 'after_fixture': str(after_root),
              'removed': sorted(before - after), 'added': sorted(after - before)}
    (after_root / 'comparison.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
