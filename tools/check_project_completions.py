#!/usr/bin/env python3
"""Read-only ownership/coverage inventory; never source or execute a project.

This is a development audit, not a runtime command catalog. Command trees stay
in their owners' parsers/metadata. The inventory names completion owners and
their checks; it does not claim that static text proves every runtime branch.
"""
import argparse
from fnmatch import fnmatchcase
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
MAX_SOURCE = 1024 * 1024

# Only ownership and validation entry points belong here, never command lists.
OWNERS = {
    'dots': (('lib/dots/completion/zsh',),
             ('python3 -B tools/test_completion_colors.py',
              'python3 -B tools/test_completion_catalog.py')),
    'anodize': (('completion/zsh',), ('python3 -B ../../tools/test_anodize_integration.py',)),
    'pkgs': (('completions/pkgs.zsh',), ('python3 -B -m unittest discover -s tests',)),
    'blastoff': (('completions/blastoff.zsh',), ('python3 -B -m unittest discover -s tests',)),
    'codex-termux': (('completions/_codex-termux',),
                     ('python3 -B tools/build.py --check', 'python3 -B tools/verify.py')),
    'battery': (('battery', 'maintenance.sh'), ('python3 -B -m unittest discover -s tests',)),
    'git-it': (('lib/completion.bash',),
               ('python3 -B -m unittest discover -s tests',)),
    'gitsub': (('gitsub',), ()),
    'paint': (('paint',), ('python3 -B tests/test_completion.py -v',)),
    'leaf': (('completions/leaf.zsh', 'src/completions.rs'), ('cargo test completions',)),
}
NON_CLI = {
    'Anodize.nvim': 'Neovim plugin', 'dots.yazi': 'Yazi plugin',
    'njen.yazi': 'Yazi configuration', 'nvim-config': 'Neovim configuration',
    '5nik7.github.io': 'website', 'njen.io': 'website', 'njen.sh': 'website',
    'resume': 'resume/document project', 'startpage': 'website',
    'wallpapers': 'image assets', 'copilot-termux': 'documentation scaffold',
    'dots.wiki': 'generated Dots documentation',
}
SEMANTIC_TAGS = (
    'command', 'commands', '*-commands', 'builtins', 'aliases', 'functions',
    'reserved-words', 'option', 'options', 'value', 'values', '*-values',
    'branch', '*branch*', 'heads', '*-heads', 'tag', 'tags', '*-tags',
    'remote', 'remotes', 'remote-names', '*-remotes',
)


def read_source(path):
    """Bounded regular source reads; no subprocesses, imports or evaluation."""
    try:
        if not path.is_file() or path.stat().st_size > MAX_SOURCE:
            return None
        return path.read_text(encoding='utf-8')
    except (OSError, UnicodeError):
        return None


def cli_evidence(root):
    """Conservative discovery, including a new project with no reviewed owner."""
    evidence = []
    manifest = read_source(root/'package.json')
    if manifest:
        try:
            if json.loads(manifest).get('bin'):
                evidence.append('package.json bin')
        except (ValueError, AttributeError):
            evidence.append('invalid package.json: review required')
    pyproject = read_source(root/'pyproject.toml') or ''
    if re.search(r'^\[(?:project\.scripts|tool\.poetry\.scripts)\]', pyproject, re.M):
        evidence.append('pyproject.toml scripts')
    if (root/'src/main.rs').is_file() or '[[bin]]' in (read_source(root/'Cargo.toml') or ''):
        evidence.append('Rust binary source')
    for candidate in (root/root.name, root/'bin', root/'completions', root/'completion'):
        if candidate.is_dir():
            evidence.append(str(candidate.relative_to(root))+' directory')
        elif (read_source(candidate) or '').startswith('#!'):
            evidence.append(str(candidate.relative_to(root))+' executable source')
    return evidence


def describe_owner(name, root):
    sources, checks = OWNERS[name]
    details = []
    missing = []
    for relative in sources:
        source = root/relative
        content = read_source(source)
        if content is None:
            missing.append(relative)
            continue
        tags = sorted(set(re.findall(r'_describe\s+(?:-[A-Za-z]+\s+)*-t\s+[\'"]?([\w-]+)', content)))
        details.append(dict(path=str(source), native_arguments='_arguments' in content,
                            explicit_tags=tags, bare_compadd='compadd' in content,
                            unmapped_tags=[tag for tag in tags if not any(fnmatchcase(tag, pattern) for pattern in SEMANTIC_TAGS)],
                            named_groups=bool(re.search(r'compadd[^\n]*\s-[JV]\b', content)),
                            compdef=sorted(set(re.findall(r'^#compdef\s+([^\n]+)', content, re.M)))))
    typed = any(d['native_arguments'] or d['explicit_tags'] or d['named_groups'] for d in details)
    unmapped = any(d['unmapped_tags'] for d in details)
    return dict(name=name, root=str(root), classification='cli',
                status='missing-source' if missing else 'unmapped-tags' if unmapped else 'reviewed-owner' if typed else 'missing-tags',
                evidence=cli_evidence(root), completion_sources=details,
                missing_sources=missing, checks=list(checks),
                verification='static inventory only; run owner checks and real menu tests',
                registration='not inspected; source ownership does not prove installed freshness')


def inventory(repos_root, dots_root=ROOT):
    repos_root = Path(repos_root).expanduser().resolve()
    dots_root = Path(dots_root).expanduser().resolve()
    records = []
    if not repos_root.is_dir():
        return [dict(name=str(repos_root), root=str(repos_root), classification='unavailable',
                     status='missing-root', evidence=['repository directory is unavailable'])]
    paths = [p for p in sorted(repos_root.iterdir()) if not p.name.startswith('.') and (p.is_dir() or p.is_symlink())]
    seen = {}
    # Dots and its bundled source owners take precedence over historical copies.
    for name, path in [('dots', dots_root), *[(n, dots_root/'plugins'/n) for n in ('anodize','pkgs','blastoff')]]:
        if path.is_dir():
            canonical = path.resolve()
            record = describe_owner(name, canonical)
            record['aliases'] = []
            records.append(record)
            seen[canonical] = record
    for path in paths:
        try:
            canonical = path.resolve(strict=True)
        except (OSError, RuntimeError):
            records.append(dict(name=path.name, root=str(path), classification='unavailable',
                                status='missing-root', evidence=['broken or unreadable project link']))
            continue
        if canonical in seen:
            seen[canonical]['aliases'].append(str(path))
            continue
        if path.name in ('pkgs','blastoff') and (dots_root/'plugins'/path.name).is_dir():
            records.append(dict(name=path.name, root=str(canonical), classification='historical-copy',
                                status='superseded', owner=str(dots_root/'plugins'/path.name),
                                evidence=['standalone source absorbed into the Dots plugin owner']))
            continue
        if path.name in OWNERS:
            record = describe_owner(path.name, canonical)
        else:
            evidence = cli_evidence(canonical)
            if path.name in NON_CLI and not evidence:
                record = dict(name=path.name, root=str(canonical), classification='non-cli',
                              status='not-applicable', evidence=[NON_CLI[path.name],
                              'no CLI manifest, named executable or completion directory found'])
            else:
                record = dict(name=path.name, root=str(canonical), classification='cli' if evidence else 'unknown',
                              status='unreviewed', evidence=evidence or ['new project: classify its command ownership'])
        record['aliases'] = []
        seen[canonical] = record
        records.append(record)
    return records


def failures(records):
    return [r for r in records if r['status'] in ('missing-source', 'missing-root', 'missing-tags', 'unmapped-tags', 'unreviewed')]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repos-root', type=Path, default=Path.home()/'repos')
    parser.add_argument('--dots-root', type=Path, default=ROOT,
                        help='Dots source owner (primarily for isolated fixtures)')
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--check', action='store_true',
                        help='fail for missing sources, unavailable roots or unreviewed projects')
    args = parser.parse_args(argv)
    records = inventory(args.repos_root, args.dots_root)
    if args.json:
        print(json.dumps(dict(schema=1, projects=records, issues=len(failures(records))), indent=2, ensure_ascii=False))
    else:
        print('Project completion source coverage (static; does not execute projects)')
        for row in records:
            print(f"{row['name']}: {row['status']} ({row['root']})")
            for source in row.get('completion_sources', []):
                tags = ', '.join(source['explicit_tags']) or 'none'
                print(f"  {source['path']}: explicit tags {tags}; native _arguments {source['native_arguments']}")
                if source['unmapped_tags']:
                    print('  Unmapped semantic tags: '+', '.join(source['unmapped_tags']))
            for missing in row.get('missing_sources', []):
                print('  Missing source: '+missing)
            for check in row.get('checks', []):
                print('  Owner check (not run): '+check)
            if row['status'] in ('unreviewed','not-applicable','superseded','missing-root'):
                print('  '+'; '.join(row['evidence']))
        print(f"{len(records)} owners/projects; {len(failures(records))} coverage issues. Installed freshness and real menu behavior require separate checks.")
    return int(args.check and bool(failures(records)))


if __name__ == '__main__':
    sys.exit(main())
