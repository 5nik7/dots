"""In-memory snapshot comparisons. Raw definitions never become trace records."""
from collections import Counter
import fnmatch
import hashlib
import math
import os
from pathlib import Path
import re

CATEGORIES = ('path', 'variables', 'functions', 'aliases', 'options')
SENSITIVE = re.compile(r'TOKEN|PASSWORD|PASSWD|SECRET|CREDENTIAL|PRIVATE_KEY|API_KEY', re.I)
VOLATILE = re.compile(r'^(?:_dots_(?:trace|record)|_DOTS_DEBUG|_DOTS_HOOK_BEFORE$|DOTS_DEBUG|BASH_|ZSH_|EPOCH|RANDOM$|SRANDOM$|SECONDS$|LINENO$|HISTCMD$|PIPESTATUS$|pipestatus$|FUNCNAME$|funcstack$|funcfiletrace$|funcsourcetrace$|functions$|dis_functions$|aliases$|galiases$|saliases$|parameters$|options$|commands$|ZSH_SUBSHELL$|_$)')


def path_changes(before, after, separator=os.pathsep):
    """Preserve empty entries and occurrences; never normalize away evidence."""
    old, new = before.split(separator), after.split(separator)
    remaining = Counter(old)
    added = []
    for index, path in enumerate(new):
        if remaining[path]: remaining[path] -= 1
        else: added.append((index, path))
    remaining = Counter(new)
    removed = []
    for index, path in enumerate(old):
        if remaining[path]: remaining[path] -= 1
        else: removed.append((index, path))
    rows = []
    for index, path in removed:
        rows.append(dict(category='path', name=path, action='removed', index=index,
                         operation='deduplicate' if path in new else 'remove'))
    for index, path in added:
        operation = 'prepend' if index == 0 else 'append' if index == len(new)-1 else 'insert'
        rows.append(dict(category='path', name=path, action='added', index=index, operation=operation))
    common=Counter(old)&Counter(new)
    def retained(paths):
        remaining=common.copy();result=[]
        for path in paths:
            if remaining[path]:result.append(path);remaining[path]-=1
        return result
    if retained(old) != retained(new):
        rows.append(dict(category='path', name='PATH', action='reordered', operation='reorder', before=old, after=new))
    return rows


class Snapshots:
    def __init__(self, selected=(), separator=os.pathsep, limit=10000, budget=None):
        self.selected = set(selected)
        self.separator = separator
        self.limit = limit
        self.previous = {}
        self.pending = {}
        self.changes = []
        self.initial_paths = {}
        self.final_paths = {}
        self.truncated = False
        self.bytes = 0
        self.budget = budget if budget is not None else [0,0]
        self.frames = {}
        self.observed = []
        self.observed_lines = False
        self.blocks = {}

    def accept(self, row):
        event, when, name, kind, value, pid = row
        if not event.startswith('state-'): return False
        try:
            if not math.isfinite(float(when)):return True
        except ValueError:return True
        if event in ('state-variable-block','state-function-block','state-option-block'):
            if pid not in self.pending:return True
            category={'state-variable-block':'variables','state-function-block':'functions','state-option-block':'options'}[event]
            identity=(pid,event,name,kind)
            fingerprint=sha(value)
            cached=self.blocks.get(identity)
            if cached and cached[0]==fingerprint:
                self.pending[pid]['values'].update(cached[1]);return True
            if event=='state-option-block':
                for option in value.splitlines():
                    self.accept(('state-options',when,option,'option','on',pid))
            elif event=='state-variable-block':
                pattern=r'(?m)^(declare|typeset|export|readonly|integer|local)\s+((?:-[^\s]+\s+)*)([A-Za-z_][A-Za-z_0-9]*)(?==|$|\s)'
                matches=list(re.finditer(pattern,value))
                private_names=set()
                for entry in re.findall(r'([A-Za-z_][A-Za-z_0-9]*):[a-z0-9_-]+:1:(?:set|unset)',value): private_names.add(entry)
                for index,match in enumerate(matches):
                    text=value[match.start():matches[index+1].start() if index+1<len(matches) else len(value)].rstrip()
                    attributes='sensitive' if name=='1' or match[3] in private_names else match[1]+' '+match[2].strip()
                    self.accept(('state-variables',when,match[3],attributes,text,pid))
            else:
                matches=list(re.finditer(r'(?m)^([^\s()]+)\s*\(\)\s*\{?\s*$',value))
                for index,match in enumerate(matches):
                    if match[1].startswith('_dots_trace') or match[1]=='TRAPDEBUG':continue
                    text=value[match.start():matches[index+1].start() if index+1<len(matches) else len(value)]
                    self.accept(('state-functions',when,match[1],'function',text,pid))
            self.blocks[identity]=(fingerprint,{key:item for key,item in self.pending[pid]['values'].items() if key[0]==category})
            return True
        if event == 'state-begin':
            if pid not in self.previous and len(self.previous)>=32:
                self.truncated=True;return True
            self.pending[pid] = dict(time=when, file=name, line=int(kind) if kind.isdigit() else None,
                                     scope=value, values={}, path=None, bytes=0, frames=[])
            self.observed_lines |= kind.isdigit() and int(kind)>0
        elif pid in self.pending:
            current = self.pending[pid]
            if event == 'state-end':
                self.finish(pid, current)
                self.pending.pop(pid, None)
            elif event == 'state-path':
                current['path'] = value
            elif event == 'state-frame':
                if not name.endswith(('/shell/trace.bash','/shell/debug.bash','/shell/record.bash')):
                    current['frames'].append(name)
            elif event.removeprefix('state-') in CATEGORIES and not VOLATILE.search(name):
                current['bytes'] += len(value.encode('utf8'))
                if current['bytes'] > 8*1024*1024:
                    self.truncated = True
                    return True
                # Store only digests plus explicitly requested safe representations.
                if event=='state-options' and name in ('SHELLOPTS','BASHOPTS'):
                    for option in value.split(':'):
                        if option:current['values'][('options',option)]=(sha('on'), 'option', 'on')
                    return True
                if event=='state-variables' and value.startswith('declare '):
                    attributes=value.split(' ',2)[1]
                    if kind!='sensitive':kind=attributes
                scalar=not re.search(r'(?:^|\s)-[a-zA-Z]*[aA]',kind)
                safe = (event=='state-variables' and name in self.selected and scalar or event=='state-options') and not SENSITIVE.search(name) and kind != 'sensitive'
                current['values'][(event[6:], name)] = (hashlib.sha256(value.encode()).hexdigest(), kind, value[:4096] if safe else None)
        return True

    def finish(self, pid, current):
        chain=[]
        for name in reversed(current['frames']):
            if not chain or name!=chain[-1]:chain.append(name)
        if chain or pid in self.frames:
            old=self.frames.get(pid,[]);common=0
            while common<min(len(old),len(chain)) and old[common]==chain[common]:common+=1
            for name in reversed(old[common:]):self.observe(('end',current['time'],name,'observed-source','0',pid))
            for name in chain[common:]:self.observe(('begin',current['time'],name,'observed-source','',pid))
            self.frames[pid]=chain
        previous = self.previous.get(pid)
        if current['path'] is not None:
            self.initial_paths.setdefault(pid, current['path'])
            self.final_paths[pid] = current['path']
        if previous and current['bytes'] <= 8*1024*1024 and previous['bytes'] <= 8*1024*1024:
            rows = []
            if current['path'] is not None and previous['path'] is not None:
                rows += path_changes(previous['path'], current['path'], self.separator)
            before, after = previous['values'], current['values']
            for key in sorted(before.keys() | after.keys()):
                old, new = before.get(key), after.get(key)
                if old == new: continue
                category, name = key
                action = 'set' if old is None else 'unset' if new is None else 'changed'
                if category in ('functions', 'aliases'):
                    action = 'created' if old is None else 'removed' if new is None else 'redefined'
                item = dict(category=category, name=name, action=action)
                if category=='options':
                    item.update(before=old[2] if old else 'off',after=new[2] if new else 'off')
                    item['action']='enabled' if item['after']=='on' else 'disabled' if item['after']=='off' else 'changed'
                if old and new and old[1] != new[1]:
                    item.update(attributes_changed=True,before_attributes=old[1],after_attributes=new[1])
                if category=='variables' and name in self.selected:
                    if SENSITIVE.search(name) or (new or old)[1] == 'sensitive': item['redacted'] = True
                    else:
                        if old and old[2] is not None: item['before'] = old[2]
                        if new and new[2] is not None: item['after'] = new[2]
                        if (new or old)[2] is None:item['value_unavailable']='non-scalar'
                rows.append(item)
            for item in rows:
                item.update(file=previous['file'], line=previous['line'], scope=previous['scope'], pid=pid,
                            observed_at_file=current['file'],observed_at_line=current['line'],
                            scope_changed=previous['scope']!=current['scope'],time=float(current['time']), precision='observation-interval')
                self.keep_change(item)
        self.previous[pid] = current

    def observe(self, record):
        if self.reserve(sum(len(v.encode()) for v in record)):self.observed.append(record)

    def reserve(self,size):
        if self.budget[0]>=self.limit or self.budget[1]+size>8*1024*1024:
            self.truncated=True;return False
        self.budget[0]+=1;self.budget[1]+=size;self.bytes+=size;return True

    def keep_change(self,item):
        if self.reserve(len(str(item).encode())):self.changes.append(item)

    def close(self, when):
        for pid,frames in self.frames.items():
            for name in reversed(frames):self.observe(('end',str(when),name,'observed-source','0',pid))


def source_location(file, line, cache):
    """Use only adjacent data manifests; never evaluate the generated guard."""
    path = Path(file)
    if path.name != 'bundle' or not line: return file, line
    if file not in cache:
        import json
        import stat
        manifest = path.with_name('manifest.json')
        try:
            if manifest.is_symlink():raise ValueError('unsafe map')
            descriptor=os.open(manifest,os.O_RDONLY|getattr(os,'O_NOFOLLOW',0)|getattr(os,'O_NONBLOCK',0))
            with os.fdopen(descriptor,'rb') as stream:
                info=os.fstat(stream.fileno())
                if not stat.S_ISREG(info.st_mode) or info.st_size>8*1024*1024:raise ValueError('unsafe map')
                data=json.loads(stream.read(8*1024*1024+1))
            rows=data.get('source_map',[]) if isinstance(data,dict) else []
            cache[file]=[r for r in rows if isinstance(r,dict) and isinstance(r.get('file'),str)
                         and all(type(r.get(k)) is int and r[k]>0 for k in ('generated_start','generated_end','line'))] if isinstance(rows,list) else []
        except (ValueError, OSError): cache[file] = []
    for row in cache[file]:
        if row['generated_start'] <= line <= row['generated_end']:
            return row['file'], row['line'] + line-row['generated_start']
    return file, line


def sha(value):
    return hashlib.sha256(value.encode()).hexdigest()


def selected_change(row, args):
    return (not getattr(args, 'file', []) or any(fnmatch.fnmatchcase(row.get('file',''), p) for p in args.file)) and (not getattr(args, 'name', []) or any(fnmatch.fnmatchcase(row.get('name',''), p) for p in args.name))
