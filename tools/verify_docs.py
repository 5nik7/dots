#!/usr/bin/env python3
"""Check repository-relative Markdown links without builds or submodule setup."""
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit

REPO = Path(__file__).resolve().parents[1]


def check_links(root):
    root = Path(root)
    files = [root / 'README.md', root / 'AGENTS.md']
    for directory in ('agents', 'docs', 'plans'):
        files.extend(sorted((root / directory).rglob('*.md')))
    checked = 0
    for path in files:
        for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)', path.read_text(encoding='utf-8')):
            parsed = urlsplit(target.strip('<>'))
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            if not (path.parent / unquote(parsed.path)).exists():
                raise RuntimeError(f'Broken relative Markdown link: {path.relative_to(root)} -> {target}')
            checked += 1
    return checked, len(files)


if __name__ == '__main__':
    try:
        links, files = check_links(REPO)
        print(f'Relative Markdown links passed ({links} links in {files} files).', file=sys.stderr)
    except (OSError, ValueError, RuntimeError) as error:
        print('Documentation verification failed: ' + str(error), file=sys.stderr)
        sys.exit(1)
