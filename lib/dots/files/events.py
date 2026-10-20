"""Optional human operation details. Never owns state, approvals or mutations."""
import sys
from catalog import Presentation
from progress import permanent_output


class OperationOutput:
    def __init__(self, enabled=False):
        self.enabled = enabled
        self.ui = None

    @classmethod
    def for_args(cls, args):
        return cls(getattr(args, 'verbose', False) and not args.json)

    def __call__(self, label, source=None, target=None, reason='', kind=None, target_kind=None):
        if not self.enabled:
            return
        try:
            if self.ui is None:
                self.ui = Presentation(sys.stderr)
            with permanent_output():
                self.ui.operation_row(label, source, target, reason, kind, target_kind)
        except Exception:
            # A failed optional display must never turn a successful write into rollback.
            self.enabled = False

    def plan(self, rows, dry_run=False):
        if not self.enabled:
            return
        reasons = {'unchanged': 'already matches the requested state',
                   'skipped': 'not applicable or unavailable',
                   'preserved': 'changed configuration kept',
                   'conflict': 'resolve the conflict before applying',
                   'excluded': 'excluded from this operation'}
        for row in rows:
            status = row.get('status', '')
            path = row.get('target') or row.get('path') or row.get('source')
            if status in reasons:
                self(status.title(), path, reason=row.get('reason') or reasons[status])
            elif dry_run:
                self('Would ' + status.replace('-', ' '), row.get('source') or path,
                     path if row.get('source') and path != row['source'] else None,
                     reason=row.get('reason', ''))
