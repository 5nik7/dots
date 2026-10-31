"""Pure goal hierarchy projection and inert FZF snapshot filtering; never opens a goal store."""
import json
import os
from pathlib import Path
import subprocess
import sys


def rank(goal):
    return ({'high':0,'normal':1,'low':2}[goal['priority']],goal['due'] or '9999-99-99',goal['created'],goal['id'])


def tree(matches,goals):
    by_id={goal['id']:goal for goal in goals};matched={g['id'] for g in matches};visible=set(matched)
    for goal in matches:
        current=goal;seen=set()
        while current.get('parent') in by_id and current['parent'] not in seen:
            seen.add(current['parent']);visible.add(current['parent']);current=by_id[current['parent']]
    children={}
    for identity in visible:
        goal=by_id[identity];parent=goal.get('parent') if goal.get('parent') in visible else None
        children.setdefault(parent,[]).append(goal)
    result=[];seen=set()
    def visit(parent,depth):
        for goal in sorted(children.get(parent,[]),key=rank):
            if goal['id'] in seen:continue
            seen.add(goal['id']);result.append((goal,depth,goal['id'] not in matched));visit(goal['id'],depth+1)
    visit(None,0)
    return result


def match_indices(snapshot,query):
    eligible=snapshot['eligible']
    if not query:return set(eligible)
    data=b''.join((str(i)+'\t'+snapshot['search'][i]+'\0').encode() for i in eligible)
    environment=dict(os.environ,FZF_DEFAULT_OPTS='',FZF_DEFAULT_OPTS_FILE='',FZF_DEFAULT_COMMAND='',BASH_ENV='',ENV='')
    result=subprocess.run(['fzf','--read0','--print0','--ansi','--delimiter=\t','--with-nth=2..','--filter='+query],input=data,capture_output=True,env=environment,timeout=5)
    if result.returncode not in (0,1):raise ValueError('goal search failed')
    matches=set()
    for record in result.stdout.split(b'\0'):
        if not record:continue
        token=record.partition(b'\t')[0]
        if not token.isdigit() or int(token) not in eligible:raise ValueError('invalid search identity')
        matches.add(int(token))
    return matches


def filtered(snapshot,query):
    matches=match_indices(snapshot,query);goals=snapshot['goals']
    positions={goal['id']:i for i,goal in enumerate(goals)}
    rows=tree([goals[i] for i in matches],goals)
    records=['header\t'+str(len(matches))+' matching goals'+(' · ancestors are read-only' if any(context for _,_,context in rows) else '')]
    for goal,depth,context in rows:
        i=positions[goal['id']];text=snapshot['context'][i] if context else snapshot['labels'][i]
        records.append(str(i)+'\t'+' '*min(128,depth*snapshot['indent'])+text)
    return ('\0'.join(records)+'\0').encode(),matches,[positions[g['id']] for g,_,_ in rows]


def main():
    # The owning browser creates a private bounded JSON transport. This helper
    # only reads it and emits inert records; there are no store/controller imports.
    path=Path(os.environ['DOTS_TODO_TREE_DATA'])
    if not path.is_file() or path.is_symlink() or path.stat().st_size>16*1024*1024:raise ValueError('unsafe tree snapshot')
    snapshot=json.loads(path.read_text())
    if snapshot.get('schema')!=1:raise ValueError('invalid tree snapshot')
    query=sys.argv[1] if len(sys.argv)==2 else ''
    sys.stdout.buffer.write(filtered(snapshot,query)[0])

if __name__=='__main__':
    try:main()
    except (ValueError,OSError,KeyError,TypeError,subprocess.SubprocessError):sys.exit(1)
