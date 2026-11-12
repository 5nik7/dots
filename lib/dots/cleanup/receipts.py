"""Private metadata-only cleanup receipts. Reads never create state."""
from pathlib import Path
import json
import os
import stat
import uuid

from files.file_platform import state_root, open_nofollow, lock, sync_dir

COUNTS = ('files', 'directories', 'symlinks', 'logical_bytes', 'allocated_bytes')


def totals(rows):
    rows = tuple(rows)
    return {key: sum(row.get(key, 0) for row in rows) for key in COUNTS}


class Receipts:
    def __init__(self, directory=None):
        self.directory = Path(directory) if directory is not None else state_root() / 'cleanup'
        self.handle = None

    def check(self):
        for path in [*reversed(self.directory.parents), self.directory]:
            if path.is_symlink():
                raise ValueError('linked cleanup receipt path: ' + str(path))
        if self.directory.exists():
            info = self.directory.stat()
            if not stat.S_ISDIR(info.st_mode) or (os.name != 'nt' and (info.st_uid != os.getuid() or info.st_mode & 0o077)):
                raise ValueError('cleanup receipts require an owner-only directory')

    def acquire(self):
        self.check()
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.check()
        fd = open_nofollow(self.directory / 'lock', os.O_CREAT | os.O_RDWR, 0o600)
        self.handle = os.fdopen(fd, 'r+b')
        try:
            lock(self.handle)
        except OSError:
            self.close()
            raise ValueError('another cleanup run is active') from None
        try:
            self.rows()  # Do not mutate if existing accounting cannot be read.
        except (OSError, ValueError):
            self.close()
            raise

    def close(self):
        if self.handle is not None:
            self.handle.close()
            self.handle = None

    def write(self, report):
        self.check()
        identity = str(uuid.UUID(report['id']))
        dest = self.directory / (identity + '.json')
        if dest.is_symlink():
            raise ValueError('linked cleanup receipt')
        temporary = self.directory / ('.' + identity + '-' + uuid.uuid4().hex)
        try:
            with os.fdopen(open_nofollow(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as output:
                json.dump(report, output, ensure_ascii=True)
                output.write('\n'); output.flush(); os.fsync(output.fileno())
            os.replace(temporary, dest)
            sync_dir(self.directory)
        finally:
            if temporary.exists():
                temporary.unlink()

    def rows(self):
        self.check()
        if not self.directory.exists():
            return []
        rows = []
        for path in self.directory.glob('*.json'):
            if str(uuid.UUID(path.stem)) != path.stem or path.is_symlink() or not path.is_file() or path.stat().st_size > 16 * 1024 * 1024:
                raise ValueError('invalid cleanup receipt: ' + str(path))
            with os.fdopen(open_nofollow(path, os.O_RDONLY)) as stream:
                row = json.load(stream)
            if not isinstance(row, dict) or row.get('schema') != 1 or row.get('id') != path.stem or not isinstance(row.get('totals'), dict):
                raise ValueError('unsupported cleanup receipt: ' + str(path))
            if any(type(row['totals'].get(k)) is not int or row['totals'][k] < 0 for k in COUNTS):
                raise ValueError('invalid cleanup receipt totals')
            if (row.get('status') not in ('running', 'completed', 'partial', 'stopped')
                    or not isinstance(row.get('started'), str) or not isinstance(row.get('groups'), list)):
                raise ValueError('invalid cleanup receipt status or groups')
            for group in row['groups']:
                if (not isinstance(group, dict) or not isinstance(group.get('group'), str)
                        or not isinstance(group.get('status'), str) or not isinstance(group.get('targets'), list)):
                    raise ValueError('invalid cleanup receipt group')
                for target in group['targets']:
                    if (not isinstance(target, dict) or not isinstance(target.get('path'), str)
                            or not isinstance(target.get('status'), str)):
                        raise ValueError('invalid cleanup receipt target')
            if row['status'] == 'running':
                row = dict(row, status='incomplete', uncertainty='An uncompleted rule is not included in verified totals.')
            rows.append(row)
        return sorted(rows, key=lambda row: row['started'], reverse=True)

    def cumulative(self):
        return totals(row['totals'] for row in self.rows())
