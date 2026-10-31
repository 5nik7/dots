"""Optional package stage shared by checkout setup adapters."""
import sys
from pathlib import Path


class Stage:
    def __init__(self, root, filename, *, json_output=False):
        sys.path.insert(0, str(Path(root)/'plugins/pkgs'))
        from pkgs_lib import manifests
        from pkgs_lib.common import config, Error
        if manifests.platform() == 'windows':
            raise ValueError('package restoration requires Termux, Linux or WSL; native Windows package backends are unavailable')
        self.core, self.error = manifests, Error
        self.check = manifests.guards(filename)
        self.document = manifests.load(filename)
        self.cfg = config()
        self.cfg['_quiet_progress'] = json_output
        self.entries = manifests.prepare(self.document, self.cfg)
        self.check()
        self.json_output = json_output

    def document_preview(self):
        return dict(schema=1, status='preview', groups=self.core.serialized(self.entries))

    def preview(self):
        self.core.preview(self.entries, self.cfg)

    def apply(self):
        self.check()
        return self.core.apply(self.document, self.cfg, data=self.json_output, check=self.check)
