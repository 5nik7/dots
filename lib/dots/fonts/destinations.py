"""Backend-owned font directories; resolve names as data, never shell expressions."""
import os
from pathlib import Path


def key(path):
    return os.path.normcase(os.path.abspath(path))


class Destinations:
    def __init__(self, root=None):
        from profile_environment import Model
        from fonts.model import digest
        self.root=Path(root or os.environ.get('DOTS') or Path(__file__).resolve().parents[3]).resolve()
        paths=[self.root/'profiles'/name/'profile.json' for name in ('linux','wsl','termux','windows')]
        paths += list((self.root/'profiles').glob('*/distros/*/profile.json'))
        paths.append(Path(__file__).resolve().parents[1]/'profile_environment.py')
        self.guards={str(p):digest(p) for p in paths}
        model=Model(self.root)
        self.names={name:path for name,path in model.scalars.items() if name.endswith('FONTS')}
        if any(digest(p)!=before for p,before in self.guards.items()):
            raise ValueError('font directory definitions changed while reading')

    def resolve(self, value):
        from fonts.model import exists, parents_safe
        name=value.removeprefix('$env:').removeprefix('$').removeprefix('{').removesuffix('}')
        path=Path(self.names[name]) if name in self.names else Path(value).expanduser()
        if not path.is_absolute():raise ValueError('--directory requires a backend *FONTS name or its absolute path')
        path=Path(os.path.abspath(path))
        aliases=[n for n,p in self.names.items() if key(p)==key(path)]
        if not aliases:raise ValueError('directory is not a Dots font directory; see fonts directories')
        parents_safe(path)
        if path.is_symlink() or exists(path) and not path.is_dir():
            raise ValueError('font directory must be an ordinary directory, not a link or file')
        return path,aliases

    def rows(self):
        groups={}
        for name,path in self.names.items():
            row=groups.setdefault(key(path),dict(path=path,names=[]))
            row['names'].append(name)
        return [dict(name=row['names'][0],aliases=row['names'][1:],path=row['path'],status='present' if Path(row['path']).is_dir() else 'not created')
                for row in groups.values()]
