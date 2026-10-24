"""Human Git identity decoration; local metadata is lazy and invocation-cached."""
import os
from pathlib import Path
import re
import shutil
import subprocess
from urllib.parse import urlsplit

GENERIC = ''
BRANCH = ''
HOSTS = dict(line.split('\t') for line in Path(__file__).with_name('git').joinpath('hosts.tsv').read_text(encoding='utf-8').splitlines())


def host_icon(host):
    return HOSTS.get(host or '', GENERIC)


def url_host(url):
    try:
        if url.lower().startswith('file://'):
            return ''
        if '://' in url:
            return (urlsplit(url).hostname or '').lower()
        if re.match(r'^(?:[^/@:]+@)?[^/:]+:', url):
            return url.split(':', 1)[0].rsplit('@', 1)[-1].lower()
    except ValueError:
        pass
    return ''


class Identities:
    def __init__(self):
        self.cache = {}
        self.aliases = None

    @staticmethod
    def read(path, *args):
        try:
            result = subprocess.run(['git', '-C', str(path), *args], stdout=subprocess.PIPE,
                                    stderr=subprocess.DEVNULL, env=dict(os.environ, GIT_OPTIONAL_LOCKS='0'))
            return result.stdout.decode('utf-8', 'surrogateescape').removesuffix('\n') if result.returncode == 0 else ''
        except OSError:
            return ''

    def host(self, path):
        if path is None:
            return ''
        key = os.path.abspath(path)
        if key not in self.cache:
            self.cache[key] = ''
            if not shutil.which('git') or any(k in os.environ for k in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE', 'GIT_COMMON_DIR')):
                return ''
            actual = self.read(path, 'rev-parse', '--show-toplevel')
            if not actual or Path(actual).resolve() != Path(path).resolve():
                return ''
            if self.aliases is None:
                self.aliases = {}
                from files.file_platform import config_root
                try:
                    config = config_root() / 'dots/git.conf'
                    if config.is_file() and not config.is_symlink():
                        values = self.read(path, 'config', '--no-includes', '--null', '--file', str(config), '--get-all', 'dots-git.hostAlias')
                        for entry in values.split('\0'):
                            if '=' in entry:
                                alias, host = entry.split('=', 1)
                                self.aliases[alias.lower()] = host.lower()
                except (OSError, ValueError):
                    pass
            branch = self.read(path, 'symbolic-ref', '--quiet', '--short', 'HEAD')
            remote = self.read(path, 'config', '--get', 'branch.' + branch + '.remote') if branch else ''
            if not remote or remote == '.': remote = 'origin'
            host = url_host(self.read(path, 'remote', 'get-url', '--', remote))
            self.cache[key] = self.aliases.get(host, host)
        return self.cache[key]
