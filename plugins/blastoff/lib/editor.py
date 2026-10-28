"""Argument-safe editor selection and recoverable staged active-config editing."""
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile


def windows_words(value):
    """Windows CRT quoting (double quotes and backslashes), no expansion."""
    words, word, quoted, started = [], [], False, False
    i = 0
    while i < len(value):
        c = value[i]
        if c.isspace() and not quoted:
            if started: words.append(''.join(word)); word=[]; started=False
            i += 1; continue
        started=True
        if c == '\\':
            j=i
            while i<len(value) and value[i]=='\\': i+=1
            n=i-j
            if i<len(value) and value[i]=='"':
                word.extend('\\'*(n//2))
                if n%2: word.append('"')
                else: quoted=not quoted
                i+=1
            else: word.extend('\\'*n)
        elif c=='"': quoted=not quoted; i+=1
        else: word.append(c); i+=1
    if quoted: raise ValueError('unclosed double quote')
    if started: words.append(''.join(word))
    return words


def resolve(core):
    configured = os.environ.get('EDITOR')
    if configured:
        try:
            args = [configured] if Path(configured).is_file() else (windows_words(configured) if os.name=='nt' else shlex.split(configured))
        except ValueError as e:
            raise core.Failure('Cannot parse EDITOR: '+str(e),3)
        if not args or not args[0]: raise core.Failure('EDITOR is empty after parsing',3)
        executable = shutil.which(args[0])
        if not executable:
            raise core.Failure('Configured EDITOR could not be found or executed: '+args[0],3)
        args[0]=executable
    else:
        args=[]
        for candidate in ('nvim','vim','vi','code','nano'):
            found=shutil.which(candidate)
            if found and Path(found).suffix.lower() not in ('.cmd','.bat','.ps1'):
                args=[found]; break
        if not args: raise core.Failure('No editor found; set EDITOR or provide nvim, vim, vi, code or nano',3)
    if Path(args[0]).suffix.lower() in ('.cmd','.bat','.ps1'):
        raise core.Failure('EDITOR must name a directly executable editor, not a shell/batch script; use an editor .exe',3)
    executable=Path(args[0]).stem.lower()
    if executable in ('code','code-insiders','codium') and '--wait' not in args: args.append('--wait')
    if executable in ('gvim','mvim') and '-f' not in args and '--nofork' not in args: args.append('-f')
    return args


def edit(core, app):
    op=core.ui_module('operations'); provenance=core.ui_module('provenance')
    argv=resolve(core)
    app.args.command='edit'
    before=op.inspect_destination(core,app,app.config,active=True)
    op.check_locks(core,app)
    # A destination inside the library is the library file, not a working copy.
    for directory in (app.themes,app.modules):
        if app.config.absolute().parent == directory.absolute():
            raise core.Failure('Active configuration is a stored library path; choose a separate STARSHIP_CONFIG')
    if app.args.dry_run:
        return op.report(app,'theme edit',[app.config],['editor argv: '+repr(argv),'back up original; edit private copy; validate and atomically publish'])
    op.interactive(core,app)
    previous,_=provenance.read_record(core,app)
    with app.mutate():
        if core.fingerprint(app.config)!=before: raise core.Failure('Active config changed before editing')
        old=core.read(app.config,links=True) if before else b''
        backup=app.backup(app.config,'config') if before else None
        core.safe_parents(app.config.parent)
        directory=Path(tempfile.mkdtemp(prefix='.blastoff-edit-',dir=app.config.parent))
        working=directory/'starship.toml'
        core.atomic(working,old)
        app.emit({},'Editing '+str(app.config)+' via '+str(working)+'; valid edits publish after the editor exits')
        success=False
        try:
            try: result=subprocess.run([*argv,str(working)],check=False)
            except OSError as e: raise core.Failure('Editor could not be launched: '+str(e),3)
            if result.returncode:
                raise core.Failure('Editor exited '+str(result.returncode)+'; active configuration unchanged',3)
            core.inspect_parents(working.parent)
            data=core.read(working); core.parsed(data)
            if core.fingerprint(app.config)!=before:
                raise core.Failure('Active config changed while editing; refusing overwrite')
            op.inspect_destination(core,app,app.config,active=True)
            if provenance.read_record(core,app)[0] != previous:
                raise core.Failure('Tracking changed while editing; edited work retained for review')
            with provenance.transaction(core,app) as commit:
                if data!=old or app.config.is_symlink() or before is None:
                    app.atomic_active(data,before)
                commit(provenance.updated(core,app,previous))
            success=True
            app.emit({'config':str(app.configured_config),'backup':backup},'Active configuration saved'+('; backup '+backup if backup else ''))
        finally:
            if success:
                working.unlink()
                # Editors may leave extra recovery files. Never recursively delete them.
                try: directory.rmdir()
                except OSError: app.diagnostic('Editor artifacts retained: '+str(directory),'warning')
            else:
                app.diagnostic('Edited work retained for recovery: '+str(working),'warning')
    return 0
