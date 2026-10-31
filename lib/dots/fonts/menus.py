"""Action-first font menus; mutations always hand off to reviewed CLI routes."""
import io

from fonts.browser import context_for,select,invoke,show_message,browse
from fonts.model import Library
from fonts.workspace import Workspace
from fonts.destinations import Destinations

HOME_ACTIONS=(('installed','Installed fonts','Inspect, copy or migrate local fonts'),
    ('set','Set application font','Choose an application and exact face'),
    ('downloaded','Downloaded fonts','Retained versions and installation destinations'),
    ('browse','Browse catalogs','Search saved provider catalogs'),
    ('directories','Font directories','Backend font storage paths'),
    ('current','Current fonts','Tracked active selections'),
    ('defaults','Saved defaults / Restore','Review and restore exact saved selections'),
    ('icons','Icon search','Search, copy, insert or print glyphs'),
    ('configuration','Configuration','Display, preview, field styles and shared layout'))


def configuration(context):
    from menus import run_action,dots_argv
    groups=(('apps.fonts','Font display and previews'),('colors.fonts','Font field styles'),
            ('icons.menu.fonts','Font icon'),('formatting.apps.cli','Command layout'),
            ('formatting.apps.menu','Menu layout and entries'),('colors.menu','Menu field styles'),
            ('colors.ui','Shared semantic styles'),('colors.status','Status styles'),
            ('apps.menu.popup','Popup appearance'))
    choice=select('Configuration',groups,context)
    if choice is not None:
        run_action(dots_argv(['config','browse','--query',choice]),kind='popup',context=context,title='fonts·configuration')
        # The child saves through Config; the next parent popup reads its changes.
        from config_values import current as controls
        from style_config import current as styles
        controls.cache_clear();styles.cache_clear()


def downloaded_rows(library):
    workspace=Workspace(library,None)
    plans=[workspace.store(str(library.directory))] if library.directory else workspace.all_stores()
    rows=[]
    for plan in plans:
        source=str(plan.library.directory) if plan.library.directory else 'personal'
        for identity,row in plan.document['families'].items():
            versions={v:r for v,r in row['versions'].items() if r.get('available',True)}
            if versions:rows.append(dict(row,id=identity,versions=versions,source=source))
    return rows


def destination(context):
    return select('Destination',[('personal','Native user installation')]+[(r['path'],r['name'],r['path']) for r in Destinations().rows()],context)


def select_row(rows,args,context,title):
    from collections import Counter
    if not hasattr(args,'_frames'):args._frames={}
    frame=args._frames.setdefault(title,dict(query=args.query or ''))
    names=Counter(r.get('name',r['id']) for r in rows)
    pairs=[]
    for i,row in enumerate(rows):
        name=row.get('name',row['id'])
        location=row.get('path',row['id'])
        if names[name]>1:name+=' · '+row.get('source','')+' · '+location
        pairs.append((str(i),name,row.get('ownership',row.get('source',''))+' · '+location))
    choice=select(title,pairs,context,frame=frame)
    return rows[int(choice)] if choice is not None else None


def installed(args,*,context=None):
    from fonts.inventory import snapshot
    context=context or context_for(args)
    while True:
        library=Library();rows,notices=snapshot(library)
        if not rows:
            show_message('\n'.join(notices) or 'No installed fonts found.',context=context,title='Installed fonts');return 0
        row=select_row(rows,args,context,'Installed fonts')
        if row is None:return 0
        if not row['supported']:
            show_message(row['reason'],context=context,title='Installed font');continue
        actions=[('set','Set application font'),('copy','Copy to Dots directory')]
        if row['migratable']:actions.append(('migrate','Migrate into Dots'))
        action=select('Installed font actions',actions,context)
        if action=='set':set_menu(args,context=context,selected=row)
        elif action in ('copy','migrate'):
            directory=select('Directory',[(r['path'],r['name'],r['path']) for r in Destinations().rows()],context)
            if directory:invoke([action,row['id'],'--directory',directory],context,library)


def downloaded(args,*,context=None):
    context=context or context_for(args)
    while True:
        library=Library(directory=args.directory)
        rows=downloaded_rows(library)
        if not rows:show_message('No downloaded fonts in this scope.',context=context,title='Downloaded fonts');return 0
        row=select_row(rows,args,context,'Downloaded fonts')
        if row is None:return 0
        action=select('Downloaded font actions',[('install','Install into a destination'),('set','Set application font'),('show','Details')],context)
        if action=='set':set_menu(args,context=context,selected=row)
        elif action=='show':invoke(['show',row['id']],context,Library(directory=None if row['source']=='personal' else row['source']))
        elif action=='install':
            version=select('Version',[(v,v) for v in reversed(row['versions'])],context)
            if version is None:continue
            target=destination(context)
            if target is None:continue
            argv=['install',row['id'],'--from',row['source'],'--version',version]
            if target!='personal':argv+=['--directory',target]
            else:
                variant=select('Variant',[(v,v) for v in sorted({f['variant'] for f in row['versions'][version]['fonts']})],context)
                if variant is None:continue
                argv+=['--variant',variant]
            # Destination is explicit above; source scope must not be appended.
            invoke(argv,context,Library())


def set_menu(args,*,context=None,selected=None):
    from fonts_cli import targets
    context=context or context_for(args);library=Library(directory=args.directory)
    target=select('Application',[(r['target'],r['target']) for r in targets(library) if r['status']=='available'],context)
    if target is None:return 0
    if selected is None:
        source=select('Font source',[('downloaded','Downloaded fonts'),('installed','Installed fonts'),('catalog','Saved catalogs')],context)
        if source is None:return 0
        if source=='installed':
            from fonts.inventory import snapshot
            rows=[r for r in snapshot(library)[0] if r['supported']]
        elif source=='downloaded':rows=downloaded_rows(library)
        else:rows=library.rows(available=True)
        selected=select_row(rows,args,context,'Select font')
        if selected is None:return 0
    argv=['set',selected['id'],'--target',target]
    source=selected.get('source')
    if 'versions' in selected:
        version=select('Version',[(v,v) for v in reversed(selected['versions'])],context)
        if version is None:return 0
        argv+=['--version',version]
        fonts=selected['versions'][version].get('fonts',[])
        if fonts:
            face=select('Face',[(f['file'],f['file'],f['family']+' · '+f['style']+' · '+f['variant']) for f in fonts
                                if target!='termux' or f['file'].lower().endswith('.ttf')],context)
            if face is None:return 0
            chosen=next(f for f in fonts if f['file']==face)
            argv+=['--face',face,'--variant',chosen['variant']]
        if source and source!='personal':argv+=['--directory',source]
    invoke(argv,context,Library())
    return 0


def home(args):
    context=context_for(args);frame={}
    while True:
        action=select('Fonts',HOME_ACTIONS,context,frame=frame)
        if action is None:return 0
        try:
            if action=='installed':installed(args,context=context)
            elif action=='set':set_menu(args,context=context)
            elif action=='downloaded':downloaded(args,context=context)
            elif action=='browse':browse(args)
            elif action=='configuration':configuration(context)
            elif action=='defaults':
                from fonts.defaults import rows
                from fonts_cli import render
                report=rows(Library());stream=io.StringIO();render(report,stream,human=True,action='defaults')
                show_message(stream.getvalue(),context=context,title='Saved defaults')
                selections=[('all','Restore all')]+[(r['selection'],'Restore '+r['selection']) for r in report['items']]
                if report['items']:
                    choice=select('Restore defaults',selections,context)
                    if choice:invoke(['restore']+([] if choice=='all' else [choice]),context,Library())
            elif action=='icons':
                from fonts.browser import icons
                from fonts.commands import parser
                icons(Library(),parser().parse_args(['icons']),context=context)
            else:invoke([action],context,Library(directory=args.directory))
        except (ValueError,OSError) as error:show_message(str(error),context=context,title='Fonts',code=1)
