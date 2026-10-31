"""Optional package-manifest snapshot for the shared Git publication workflow."""
import json
from pathlib import Path
import sys
from types import SimpleNamespace


class Stage:
    def __init__(self, root, *, quiet=False):
        sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'plugins/pkgs'))
        from pkgs_lib import manifests
        from pkgs_lib.common import config, Error
        self.error = Error
        try:
            path = manifests.default_path(root)
            args = SimpleNamespace(manager=None, global_scope=False, include_dependencies=False,
                                   pin_versions=False, dry_run=quiet, json=quiet)
            self.snapshot = manifests.Update(path, args, config(), root=root, profile_default=True)
            self.path = self.snapshot.path
            self.content = json.dumps(self.snapshot.document, indent=2, ensure_ascii=False)+'\n'
        except Error as error:
            raise ValueError(str(error)) from None

    def verify(self):
        try: self.snapshot.verify()
        except self.error as error: raise ValueError(str(error)) from None

    def apply(self):
        try: self.snapshot.save(SimpleNamespace(dry_run=False, yes=True), emit=False)
        except self.error as error: raise ValueError(str(error)) from None
