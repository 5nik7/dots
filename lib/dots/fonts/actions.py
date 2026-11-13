"""Batch transfers share one preflight and one durable transaction."""
from fonts import operations as ops
from fonts.payloads import retain
from fonts.workspace import Workspace
from progress import tracked, report, sequence


@tracked('Preparing font transfers')
def transfer(library,args,temporary):
    with sequence('Prepare font transfer', 2) as preparation:
        with preparation.step('Prepare selected fonts'):
            workspace=Workspace(library,temporary)
            target=workspace.store(str(library.directory)) if library.directory else workspace.user
            queries=args.operand if isinstance(args.operand,list) else [args.operand]
            if args.action in ('copy','migrate'):
                if not library.directory:raise ValueError('copy/migrate requires a destination --directory')
                from fonts.inventory import snapshot,select,import_row,migrate
                rows,_=snapshot(workspace.user.library)
                selected = select(rows,queries)
                with sequence('Prepare font files', len(selected), unit='file') as files:
                    for index, row in enumerate(selected):
                        with files.step(row['path']):
                            report('Preparing font '+args.action+' · files', index, len(selected))
                            identity,version,face=import_row(workspace,row,rows)
                            retain(workspace.user,target,identity,version,temporary,faces=[face])
                            if args.action=='migrate':
                                migrate(workspace,row,identity,version,face)
                                if row['path']==str(workspace.user.library.home/'.termux/font.ttf'):
                                    from fonts.config import configure
                                    font=next(f for f in workspace.user.document['families'][identity]['versions'][version]['fonts'] if f['file']==face)
                                    configure(workspace.user,identity,version,font,'termux')
                            workspace.user.items.append(dict(id=identity,version=version,action=args.action,path=str(target.library.directory)))
            else:
                if library.directory and args.variant:raise ValueError('directory storage retains every available variant; choose --variant when using it')
                if args.version and len(queries)!=1:raise ValueError('--version requires one family; batch installation uses each preferred version')
                selected = list(dict.fromkeys(queries))
                with sequence('Prepare font families', len(selected), unit='family') as families:
                    for index, query in enumerate(selected):
                        with families.step(query), sequence('Prepare font family', 2) as stages:
                            with stages.step('Obtain font'):
                                report('Preparing font install · '+query+' · families', index, len(selected))
                                identity=workspace.resolve(query,args.from_,catalog=True)
                                source,version=workspace.obtain(identity,args.version,args.from_,dry_run=args.dry_run,download_target=target)
                                if source is None:continue
                                record=source.document['families'][identity]['versions'][version]
                                if not library.directory and record.get('partial'):
                                    variants={f['variant'] for f in record['fonts']}
                                    variant=args.variant or ('mono' if 'mono' in variants else 'original' if 'original' in variants else sorted(variants)[0])
                                    source,version=workspace.obtain(identity,version,None,dry_run=args.dry_run,required_variant=variant)
                                    if source is None:continue
                            with stages.step('Prepare installation'):
                                before=len(workspace.user.operations)
                                if source is not target:retain(source,target,identity,version,temporary)
                                if not library.directory:
                                    ops.install(target,identity,version,args.variant)
                                    if source.library.directory:target.document['families'][identity]['installed']['directory']=source.library.directory_key
                                if len(workspace.user.operations)==before:workspace.user.items.append(dict(id=identity,version=version,action='already present'))
        with preparation.step('Finalize font plan'):
            report('Prepared font '+args.action, len(selected), len(selected))
            from fonts.defaults import synchronize
            synchronize(workspace)
            return workspace.finish()
