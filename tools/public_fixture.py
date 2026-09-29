"""Copy public repository trees without retaining links into the live checkout."""
import os
from pathlib import Path
import shutil


def copy_public_tree(source, target, *, repo, fixture, aliases=()):
    source, target = Path(source), Path(target)
    roots = [Path(root).resolve() for root in (repo, *aliases)]
    links = []
    # Preflight links before copying. Never dereference a foreign link for data.
    for path in source.rglob('*'):
        if not path.is_symlink():
            continue
        resolved = path.resolve()
        for root in roots:
            if resolved.is_relative_to(root):
                links.append((path.relative_to(source), resolved.relative_to(root)))
                break
        else:
            raise ValueError('Public fixture link escapes source repository: ' + str(path))
    shutil.copytree(source, target, symlinks=True)
    for relative, destination in links:
        link = target / relative
        link.unlink()
        link.symlink_to(os.path.relpath(Path(fixture) / destination, link.parent))
