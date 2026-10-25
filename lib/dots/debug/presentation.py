"""Nested diagnostic views using the shared resource and semantic renderer."""
import fnmatch
from .changes import selected_change


def duration(value):
    return 'not measured' if value is None else f'{value:.2f} ms'


class Tree:
    def __init__(self, ui, args=None):
        self.ui, self.args, self.count, self.hidden = ui, args, 0, 0

    def row(self, name, depth=0, time=None, path=None, role='branch', suffix=''):
        if self.count>=getattr(self.args,'limit',10000) or getattr(self.args,'depth',None) is not None and depth>self.args.depth:
            self.hidden+=1;return
        self.count+=1
        depth=min(depth,max(0,(self.ui.width-20)//2))
        markers=('●','➜','★','‒') if self.ui.icons else ('*','>','+','-')
        prefix='  '+'  '*depth+markers[depth%4]+' '
        style=self.ui.resources.git_style(role)
        label=self.ui.path(name) if path else name
        if path:
            _,icon,style=self.ui.resources.describe(path,None,None)
            if self.ui.icons:label=icon+' '+label
        spans=[(label,style)]
        if time is not None:spans.append(('  '+duration(time),self.ui.resources.git_style('clean')))
        if suffix:spans.append(('  '+suffix,self.ui.resources.git_style('modified')))
        self.ui._spans(spans,prefix,self.ui.resources.git_style('branch'),continuation_prefix=' '*len(prefix))

    def change(self, row, depth):
        action=row['action'];name=row['name'] or '(empty PATH entry)'
        role='deleted' if action in ('unset','removed') else 'clean' if action in ('set','added','created') else 'modified'
        category=row['category']
        self.row(category+' '+name+' · '+action,depth,role=role)
        origin=self.ui.path(row.get('file') or 'unknown')
        if row.get('line'):origin+=':'+str(row['line'])
        if row.get('observed_at_file')==row.get('file') and row.get('observed_at_line') and row['observed_at_line']!=row.get('line'):
            origin+=' to '+str(row['observed_at_line'])
        elif row.get('observed_at_file') and row['observed_at_file']!=row.get('file'):
            origin+=' to '+self.ui.path(row['observed_at_file'])+(':'+str(row['observed_at_line']) if row.get('observed_at_line') else '')
        detail=row.get('operation',row.get('scope',''))
        if detail:origin=detail+' · '+origin
        origin+=' · +'+duration(row.get('offset_ms'))+' · '+row.get('precision','observed')
        self.row(origin,depth+1,role='modified')
        for key in ('before','after'):
            if key in row:self.row(key+': '+str(row[key]),depth+1)
        if row.get('redacted'):self.row('value redacted',depth+1)
        if row.get('attributes_changed'):self.row('attributes '+row['before_attributes']+' -> '+row['after_attributes'],depth+1)
        if row.get('value_unavailable'):self.row('value omitted: '+row['value_unavailable'],depth+1)
        if row.get('scope_changed'):self.row('scope changed; visibility may have changed',depth+1)

    def finish(self):
        if self.hidden:self.ui.detail('Collapsed',str(self.hidden)+' rows; adjust --depth/--limit')


def render(data, action, view='tree', args=None):
    from files.catalog import Presentation
    ui=Presentation();ui.heading('Dots debug '+action);tree=Tree(ui,args)
    if action=='startup':
        ui.detail('Mode',data['mode']);ui.detail('Shell',data['shell'])
        if data['mode']=='plan':
            ui.detail('Note',data['note'])
            for row in data['steps']:tree.row(row['name'],1,path=row['name'] if row['kind']!='phase' else None)
            ui.detail('Execute','Add --live or --isolated to measure startup');tree.finish();return
        for index,sample in enumerate(data['runs'],1):
            ui.emit();tree.row('Run '+str(index)+' · '+sample['status'],time=sample.get('startup_ms'))
            if sample.get('coverage'):ui.detail('Coverage',sample['coverage'])
            ui.detail('Process',duration(sample.get('process_ms')))
            events=sample['events'];changes=[r for r in sample.get('changes',[]) if selected_change(r,args)]
            if view=='summary':
                tree.row(str(len(events))+' events · '+str(len(changes))+' changes',1);continue
            by_id={e.get('id',i+1):e for i,e in enumerate(events)}
            selected=set()
            for identity,event in by_id.items():
                file_match=not getattr(args,'file',[]) or any(fnmatch.fnmatchcase(event['name'],p) for p in args.file)
                name_match=not getattr(args,'name',[]) or any(fnmatch.fnmatchcase(event['name'],p) for p in args.name)
                if file_match and name_match and (event.get('duration_ms') or 0)>=getattr(args,'min_ms',0):selected.add(identity)
            selected.update(r['parent_id'] for r in changes if r.get('parent_id'))
            for identity in list(selected):
                visited=set()
                while identity in by_id and identity not in visited:
                    visited.add(identity);selected.add(identity);identity=by_id[identity].get('parent_id')
            sequence=list(by_id.items())
            if view=='slowest':sequence=sorted(((i,e) for i,e in sequence if e.get('duration_ms') is not None),key=lambda pair:pair[1]['duration_ms'],reverse=True)
            attached=set()
            for identity,event in sequence:
                if identity not in selected:continue
                depth=1+(event.get('depth',0) if view!='slowest' else 0)
                state=event.get('status','observed')
                suffix=state if state not in ('completed','observed') else ''
                if event.get('precision')=='observed-interval':suffix=(suffix+' · ' if suffix else '')+'observed interval'
                if event.get('self_ms') is not None:suffix+=((' · ' if suffix else '')+'self '+duration(event['self_ms']))
                if event.get('duration_ms') is None:suffix=(suffix+' · ' if suffix else '')+('entry only' if event['kind']=='source-entry' else 'unmeasured')
                tree.row(event['name'],depth,event.get('duration_ms'),event['name'] if event['kind'] not in ('phase','cache') else None,suffix=suffix)
                for n,change in enumerate(changes):
                    if change.get('parent_id')==identity:tree.change(change,depth+1);attached.add(n)
            remaining=[r for n,r in enumerate(changes) if n not in attached]
            if remaining:
                tree.row('Changes outside paired module timings',1)
                for row in remaining:tree.change(row,2)
            if sample.get('truncated'):ui.detail('Coverage','Capture limit reached; partial trace')
            if sample.get('note'):ui.detail('Note',sample['note'])
        ui.emit();ui.detail('Median',duration(data['summary']['median_ms']));ui.detail('Range',duration(data['summary']['min_ms'])+' – '+duration(data['summary']['max_ms']))
    elif action in ('path','record'):
        ui.detail('Recording',data.get('recording',data.get('status','unrecorded')))
        if data.get('mode'):ui.detail('Mode',data['mode'])
        ui.detail('Note',data.get('note',''))
        if data.get('truncated'):ui.detail('Coverage','Recording limit reached; history is partial')
        if action=='record' or getattr(args,'history',False):
            for row in data.get('history',[]):tree.change(row,0)
            if not data.get('history'):tree.row('No recorded changes')
        else:
            for row in data['rows']:
                tree.row(str(row['order'])+' '+ui.path(row['path']),path=row['path'])
                tree.row(row.get('provenance','inherited; origin unknown'),1)
                tree.row('Owner '+row['source']+(' · missing' if not row['exists'] else '')+(' · duplicate' if row['duplicate'] else ''),1)
                for change in row.get('history',[]):tree.change(change,1)
                if row.get('command'):tree.row(('Selected ' if row['selected'] else 'Shadowed ')+ui.path(row['command']),1,path=row['command'])
    else:
        rows=data.get('checks',data.get('rows',[]))
        for key,value in data.items():
            if key in ('version','checks','rows','exit_code') or value is None:continue
            tree.row(key.replace('_',' ').capitalize())
            for item in value if isinstance(value,list) else [value]:tree.row(str(item),1,path=str(item) if key in ('path','selected','roots','candidates') and str(item).startswith(('/','C:')) else None)
        for row in rows:
            name=row.get('name',row.get('path',row.get('suite','Result')))
            tree.row(str(name),time=row.get('elapsed_ms'),path=row.get('path'),suffix=row.get('status',''))
            for key,value in row.items():
                if key in ('name','path','elapsed_ms','status') or value is None:continue
                for item in value if isinstance(value,list) else [value]:tree.row(key.capitalize()+': '+str(item),1)
        if 'checks' in data:
            ui.detail('Result',', '.join(str(sum(r.get('status')==s for r in rows))+' '+s for s in ('passed','failed','skipped')))
    tree.finish()
