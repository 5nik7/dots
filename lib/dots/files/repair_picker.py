#!/usr/bin/env python3
"""Interactive repair decisions and inert metadata previews; never applies."""
import json
import os
from pathlib import Path
import re
import sys
import tempfile

from catalog import Presentation
from interaction import RichSelector
from picker import fzf_colors


ACTIONS = {'link': 'Queue link to catalog source',
           'relink': 'Relink to catalog source',
           'replace-with-backup': 'Back up and replace with catalog link'}


def details(ui, item):
    ui.heading('File repair review')
    if 'message' in item:
        ui.detail('Review', item['message'])
        return
    ui.detail('Resource', item['id'], '94')
    ui.detail('Decision', item['decision'], '96')
    ui.resource_detail('Source', item['source'])
    ui.resource_detail('Target', item['target'])
    ui.detail('Current', item['target_kind'] or 'See reason below')
    if item['current_link']:
        ui.detail('Link', item['current_link'])
    ui.detail('Reason', item['reason'])
    ui.detail('Backup', item['backup'])
    if item['next_step']:
        ui.detail('Next step', item['next_step'])


class RepairHelper:
    def __init__(self, repair, selector=None):
        self.repair = repair
        self.selector = selector or RichSelector()
        self.ui = Presentation()

    def item(self, identity):
        row, finding = self.repair.rows[identity], self.repair.findings[identity]
        hints = {
            'protected-theme': 'dots theme files check',
            'catalog-conflict': 'dots files list --status conflict; dots files show ' + identity,
            'mapping': 'dots files show ' + identity + '; dots files edit ' + identity,
            'other-owner': 'dots files show ' + identity + '; review the named owner before changing ownership.',
            'source-unavailable': 'Restore the source, then run dots files repair ' + identity,
            'unsafe-path': 'dots files show ' + identity + '; resolve the unsafe path manually.',
            'inspection-error': 'dots files show ' + identity + '; resolve the inspection error and scan again.',
        }
        decision = self.repair.choices.get(identity)
        return dict(id=identity, source=row['source'], target=row['target'],
                    decision=('Queued: ' + decision.replace('-', ' ')) if decision else
                             ('Skipped for this run' if identity in self.repair.skipped else 'Unresolved'),
                    target_kind=finding.target_kind, current_link=finding.current_link,
                    reason=finding.reason,
                    backup=('Current destination retained for undo; original installation baseline preserved.'
                            if finding.target_kind != 'missing' else 'Undo removes the new link.')
                           if finding.resolution else 'No replacement is available in this helper.',
                    next_step=hints.get(finding.issue, ''))

    def pick(self, title, entries):
        """Numeric tokens map to stable actions, never to parsed display text."""
        labels = [self.ui.clean(label) for _, label, _ in entries]
        if self.selector.backend == 'fzf':
            # Private, temporary metadata only. No source or target contents.
            with tempfile.TemporaryDirectory(prefix='dots-repair-picker-') as directory:
                snapshot = Path(directory) / 'items.json'
                snapshot.write_text(json.dumps(dict(items=[item for _, _, item in entries],
                                                    color=self.ui.color, icons=self.ui.icons)))
                snapshot.chmod(0o600)
                prefix = '"$DOTS_REPAIR_PYTHON" -B "$DOTS_REPAIR_HELPER" "$DOTS_REPAIR_SNAPSHOT" {1}'
                if os.name == 'nt':
                    prefix = '& $env:DOTS_REPAIR_PYTHON -B $env:DOTS_REPAIR_HELPER $env:DOTS_REPAIR_SNAPSHOT {1}'
                preview = (prefix, '', dict(DOTS_REPAIR_PYTHON=sys.executable,
                           DOTS_REPAIR_HELPER=str(Path(__file__).resolve()), DOTS_REPAIR_SNAPSHOT=str(snapshot),
                           DOTS_PROGRESS='never', DOTS_OPERATION_VERBOSE='0'))
                selected = self.selector.pick(title, labels, preview=preview, color=self.ui.color,
                                              icons=self.ui.icons, colors=fzf_colors(self.ui), include_cancel=False)
        else:
            selected = self.selector.pick(title, labels, color=self.ui.color, icons=self.ui.icons, include_cancel=False)
        if (len(selected) != 1 or type(selected[0]) is not int or not 0 <= selected[0] < len(entries)):
            raise ValueError('invalid repair selection; scan again')
        return entries[selected[0]][0]

    def run(self):
        identities = [identity for identity, finding in self.repair.findings.items()
                      if finding.action == 'unresolved' or finding.resolution and finding.action != 'unchanged']
        while True:
            self.repair.verify()
            count = len(self.repair.choices)
            entries = [('cancel', 'Cancel repairs', {'message': 'Discard all queued decisions without applying.'}),
                       ('review', f'Review queued repairs ({count})' if count else 'Finish without repairs',
                        {'message': 'Review the complete batch, then approve once to apply. Default is Cancel.'})]
            for identity in identities:
                item = self.item(identity)
                entries.append((identity, identity + ' | ' + item['decision'], item))
            chosen = self.pick('File repair issues', entries)
            if chosen == 'cancel':
                return False
            if chosen == 'review':
                self.repair.verify()
                return True
            finding = self.repair.findings[chosen]
            if finding.resolution:
                self.repair.prepare(chosen)
            item = self.item(chosen)
            if self.selector.backend != 'fzf':
                details(self.ui, item)
            actions = [('back', 'Back', item), ('skip', 'Skip for this run', item)]
            if finding.resolution:
                actions.append((finding.resolution, ACTIONS[finding.resolution], item))
            action = self.pick('Review ' + chosen, actions)
            if action != 'back':
                self.repair.select(chosen, None if action == 'skip' else action)


def preview(snapshot, token):
    doc = json.loads(Path(snapshot).read_text())
    if not re.fullmatch(r'0|[1-9][0-9]*', token) or int(token) >= len(doc['items']):
        raise ValueError('unknown repair preview token')
    os.environ.update(DOTS_COLOR='always' if doc['color'] else 'never',
                      DOTS_ICONS='always' if doc['icons'] else 'never')
    ui = Presentation()
    ui.width = max(24, int(os.environ.get('FZF_PREVIEW_COLUMNS', ui.width)))
    details(ui, doc['items'][int(token)])


if __name__ == '__main__':
    try:
        if len(sys.argv) != 3:
            raise ValueError('private repair preview helper')
        preview(*sys.argv[1:])
    except (OSError, ValueError, KeyError, TypeError):
        print('Repair preview unavailable.')
        sys.exit(1)
