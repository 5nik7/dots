"""Explicit irreversible cleanup, with per-rule verified durable subtotals."""
from datetime import datetime, timezone
from pathlib import Path
import os
import time
import uuid

from .core import inside, inventory, measure, public, references, removed, delete_entries
from .receipts import totals


def now():
    return datetime.now(timezone.utc).isoformat()


def available(path):
    import shutil
    return shutil.disk_usage(path).free


def run(adapter, targets, groups, issues, store, confirm, progress=lambda *args: None, inspect=references):
    started = time.monotonic()
    report = dict(schema=1, id=None, platform='termux', started=now(), status='running',
                  selected_groups=list(groups), groups=[], issues=list(issues), totals=totals([]),
                  available_before=available(adapter.boundary))
    locked = False
    try:
        for group in groups:
            members = [target for target in targets if target.group == group]
            if not members:
                continue
            decision = confirm(group, members)
            if decision == 'stop':
                report['status'] = 'stopped'
                break
            if decision != 'delete':
                report['groups'].append(dict(group=group, status='skipped', targets=[], reason='user skipped'))
                continue
            if not locked:
                store.acquire(); locked = True
                report['id'] = str(uuid.uuid4())
            row = dict(group=group, status='running', targets=[])
            report['groups'].append(row)
            store.write(report)
            # Preflight the entire approved group before its first mutation.
            try:
                active, unknown = inspect([target.path for target in members])
                if active or unknown:
                    raise ValueError('active or uninspectable processes; group retained')
                for target in members:
                    for protected in (Path.cwd().resolve(), Path(__file__).resolve(), store.directory):
                        if inside(protected, target.path):
                            raise ValueError('target contains the working directory, executing code or receipts')
                    if inventory(target, adapter.boundary) != target.entries:
                        raise ValueError('changed since scan: ' + str(target.path))
            except (ValueError, OSError) as error:
                row.update(status='blocked', reason=str(error))
                store.write(report)
                continue
            for target in members:
                result = dict(rule=target.rule, path=str(target.path), status='pending', deleted=totals([]))
                row['targets'].append(result)
                store.write(report)  # Failure here prevents the deletion.
                confirmed = {}
                native = target.rule in ('go-module-cache', 'go-build-cache', 'uv-cache')
                interrupted = False
                try:
                    active, unknown = inspect([target.path])
                    if active or unknown:
                        raise ValueError('target became busy or process inspection failed')
                    if inventory(target, adapter.boundary) != target.entries:
                        raise ValueError('target changed before deletion')
                    progress('Cleaning ' + target.rule)
                    if native:
                        adapter.native(target)
                    else:
                        delete_entries(target, adapter.boundary, progress, confirmed)
                    result['status'] = 'completed'
                except KeyboardInterrupt:
                    interrupted = True
                    result['status'] = 'interrupted'
                except (ValueError, OSError) as error:
                    result.update(status='failed', reason=str(error))
                # Direct operations count only our successful unlinks. Native tools
                # are verified against the inventory; failed tools remain uncertain.
                if not native:
                    result['deleted'] = measure(confirmed)
                try:
                    after = inventory(target, adapter.boundary)
                    result['remaining'] = measure(after)
                    if native and result['status'] == 'completed':
                        result['deleted'] = removed(target.entries, after)
                    elif native:
                        result['uncertainty'] = 'Native cleanup did not finish; unconfirmed removal is excluded from totals.'
                except (ValueError, OSError) as error:
                    result.update(status='failed', reason='verification failed: ' + str(error))
                report['totals'] = totals(item['deleted'] for g in report['groups'] for item in g['targets'])
                store.write(report)
                if interrupted:
                    raise KeyboardInterrupt
            row['status'] = 'completed' if all(item['status'] == 'completed' for item in row['targets']) else 'partial'
            store.write(report)
        if report['status'] == 'running':
            report['status'] = 'partial' if issues or any(g['status'] in ('partial', 'blocked') for g in report['groups']) else 'completed'
    except KeyboardInterrupt:
        report['status'] = 'stopped'
    except (ValueError, OSError) as error:
        report['status'] = 'partial'
        report['issues'].append(dict(reason=str(error)))
    finally:
        report.update(finished=now(), duration_seconds=round(time.monotonic() - started, 3),
                      available_after=available(adapter.boundary))
        report['available_change'] = report['available_after'] - report['available_before']
        try:
            if locked:
                store.write(report)
        finally:
            store.close()
    report['cumulative'] = store.cumulative()
    return report
