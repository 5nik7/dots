"""Optional package stage shared by checkout setup adapters."""
import sys
from pathlib import Path


class Stage:
    def __init__(self, root, filename=None, *, document=None, json_output=False):
        sys.path.insert(0, str(Path(root)/'plugins/pkgs'))
        from pkgs_lib import manifests
        from pkgs_lib.common import config, Error
        self.core, self.error = manifests, Error
        self.check = manifests.guards(filename) if filename else lambda: None
        self.document = manifests.validate(document) if document is not None else manifests.load(filename)
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
        return self.core.apply(self.document, self.cfg, data=self.json_output, check=self.check, stop_on_failure=True)
