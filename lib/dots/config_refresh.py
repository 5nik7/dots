"""Journaled visual-only publication. Reads and previews never activate consumers."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import stat
import sys
import tempfile
import uuid

from profile_config import checkout, context
from style_config import Styles, ROLES
from style_catalog import APPS, consumers
from theme_styles import snapshot, tokens, write
from files.file_platform import state_root
from files.transactions import Store, digest, parents_safe

LIB = Path(__file__).resolve().parent


def read_json(path):
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 4*1024*1024:
        raise ValueError('missing or unsafe visual snapshot: '+str(path))
    return json.loads(path.read_text())


def active(state):
    pointer = state/'current/theme'
    parents_safe(pointer)
    if not pointer.exists() and not pointer.is_symlink(): return None
    if not pointer.is_symlink(): raise ValueError('unmanaged active theme pointer')
    generation = pointer.resolve(strict=True)
    if generation.parent != state/'themes/generations' or not re.fullmatch(r'g\.[a-zA-Z0-9]+', generation.name):
        raise ValueError('unmanaged active theme generation')
    if (generation/'status').read_text().strip() != 'committed': raise ValueError('theme publication requires recovery')
    if (state/'themes/current').read_text().strip() != generation.name: raise ValueError('theme publication pointers disagree')
    return generation


def effective(root=None):
    style = Styles(root)
    return snapshot(style.palette, style.root)


def affected(before, after):
    return [app for app in APPS if before.get('apps',{}).get(app) != after.get('apps',{}).get(app)]


def explain(key, root=None, selected=None, defaults=False, app=None, *, _style=None, _published=None, _active=None):
    style = _style or Styles(root, selected, defaults=defaults)
    group, _, name = key.partition('.')
    if group not in ('icons','colors') or not name: raise ValueError('explain requires an individual icon or color field')
    choices = consumers(group,name)
    if app and app not in APPS: raise ValueError('unknown visual consumer')
    rows=[]
    if _published is None:
        try:
            generation=active(state_root())
            published=read_json(generation/'preferences.json') if generation else {}
        except (OSError,ValueError): published={}
    else: published=_published
    from style_catalog import split, canonical
    embedded,base=split(name)
    if embedded and app and embedded != app:
        raise ValueError('--app conflicts with the consumer in the key')
    if group=='icons': base=canonical(base)
    for consumer in [app or embedded] if app or embedded else choices or [None]:
        resolved=style.resolve(group,name,consumer)
        is_active=not defaults and style.selected['current']==(_active or context(style.root)['current'])
        actual=published.get('apps',{}).get(consumer,{}).get(group,{})
        if group=='colors':
            role,_,field=base.rpartition('.'); actual=actual.get(role,{}).get(field)
            expected=style.color(resolved['value']) if field in ('fg','bg') and resolved['value'] is not None else resolved['value']
        else: actual=actual.get(base); expected=resolved['value']
        status=('unsupported' if consumer not in choices else 'inactive scope' if not is_active else
                'next invocation' if consumer=='cli' else 'published' if actual==expected and published else 'pending')
        rows.append(dict(app=consumer,supported=consumer in choices,refresh=status,**resolved))
    return dict(schema=1,key=key,profile='defaults' if defaults else style.selected['current'],consumers=rows)


def inline_color(text, table, key, field, value):
    """Change one owned generated TOML color, preserving the remaining document."""
    import tomllib
    before = tomllib.loads(text)
    expected = json.loads(json.dumps(before))
    existing = expected.setdefault(table, {}).setdefault(key, {})
    if not isinstance(existing, dict): raise ValueError('unsupported generated Yazi style')
    existing[field] = value
    section = re.search(r'(?ms)^\['+re.escape(table)+r'\]\s*\n(.*?)(?=^\[|\Z)', text)
    if not section:
        text += '\n['+table+']\n'+key+' = { '+field+' = '+json.dumps(value)+' }\n'
    else:
        body = section[1]
        line = re.search(r'(?m)^'+re.escape(key)+r'\s*=\s*\{([^\n]*)\}([^\n]*)$', body)
        if line:
            fields = line[1]
            pattern = r"(?<![a-z_])"+re.escape(field)+r"\s*=\s*(?:\"[^\"]*\"|'[^']*')"
            replacement = field+' = '+json.dumps(value)
            if re.search(pattern, fields): fields = re.sub(pattern, lambda _: replacement, fields)
            else: fields = fields.rstrip()+', '+replacement
            body = body[:line.start(1)]+fields+body[line.end(1):]
        elif re.search(r'(?m)^'+re.escape(key)+r'\s*=',body): raise ValueError('unsupported generated Yazi style')
        else: body += key+' = { '+field+' = '+json.dumps(value)+' }\n'
        text = text[:section.start(1)]+body+text[section.end(1):]
    if tomllib.loads(text) != expected: raise ValueError('Yazi visual change would modify unrelated values')
    return text


def render_visual(out, root, palette, doc, changed):
    sys.path.insert(0, str(LIB/'themes'))
    from palette_native import styles as file_styles
    style=Styles(root,palette=palette)
    write(out,palette,root)
    if (out/'colors.json').is_file():
        color_doc=read_json(out/'colors.json');color_doc['preferences']=doc
        (out/'colors.json').write_text(json.dumps(color_doc,sort_keys=True)+'\n')
        (out/'colors.lua').write_text('return '+file_styles().lua(color_doc)+'\n')
    else: raise ValueError('published file-color snapshot is missing')
    values=dict(palette)
    values.update({'git_'+k:v for k,v in color_doc.get('colors',{}).get('git',{}).items()})
    values.update(tokens(palette,root))
    for app,name in [('tmux','tmux.conf'),('fzf','fzf.sh'),('gum','gum_env.sh')]:
        if app not in changed: continue
        template=(root/'default/themed'/(name+'.tpl')).read_text()
        def replace(match):
            if match[1] not in values: raise ValueError('unknown visual template token: '+match[1])
            return values[match[1]]
        rendered=re.sub(r'\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}',replace,template)
        if '{{' in rendered or '}}' in rendered: raise ValueError('unresolved visual template')
        if app=='tmux':
            from tmux_config import layout
            placement='# Dots configuration placement\n'+layout(root,style.selected)
            base_config = root/'config/tmux/tmux.conf'
            if base_config.is_file():
                for line in base_config.read_text().splitlines():
                    if line.startswith('set -g @dots-window-idle-style ') and '#(' not in line:
                        rendered += line+'\n'
            # Source only our literal fragment during activation, never arbitrary config.
            (out/'tmux.visual.conf').write_text(rendered+placement)
            old=(out/name).read_text().split('# Dots configuration placement\n')[0]
            for line in rendered.splitlines():
                if not line.startswith(('set ', 'setw ')): continue
                option=line.split()[2]
                pattern=r'(?m)^(?:set|setw) -g '+re.escape(option)+r' .*$'
                if re.search(pattern,old): old=re.sub(pattern,lambda _:line,old)
                else: old+='\n'+line+'\n'
            rendered=old+placement
        (out/name).write_text(rendered)
    if 'yazi' in changed:
        path=out/'yazi.toml';text=path.read_text();icons=values['file_icons_yazi']+'\n'
        for table,key,field in [('mgr','cwd','fg'),('tabs','active','bg'),('status','progress_normal','fg'),('mode','normal_main','bg')]:
            text=inline_color(text,table,key,field,values['yazi_ui_accent_fg'])
        pattern=r'(?ms)^\[icon\]\s*\n.*?(?=^\[(?!icon\.)|\Z)'
        text=re.sub(pattern,lambda _:icons,text) if re.search(pattern,text) else text+'\n'+icons
        path.write_text(text);(out/'yazi/flavor.toml').write_text(text)
    from theme_styles import write_shell
    write_shell(out, style, doc)


def tmux_servers(root, selected, state):
    """Bounded existing topology plus the inherited/default server; never start one."""
    from menu_sessions import Server
    from codex_attention import load, socket_key
    executable=shutil.which('tmux')
    if os.name=='nt' or not executable: return [],[]
    paths={x['socket'] for x in load()}
    try:
        server=Server.discover()
        if server: paths.add(server.socket)
    except (OSError,ValueError): pass
    good,skipped=[],[]
    for socket in sorted(paths)[:16]:
        try:
            info=Path(socket).stat()
            if not stat.S_ISSOCK(info.st_mode) or info.st_uid!=os.getuid(): raise ValueError('foreign tmux socket')
            key=socket_key(socket)
            result=subprocess.run([executable,'-N','-S',socket,'display-message','-p','#{pid}'],capture_output=True,text=True,timeout=3)
            if result.returncode or not result.stdout.strip().isdigit(): raise ValueError('unavailable server')
            server=Server(executable,socket,int(result.stdout.strip()))
            env={}
            for name in ('DOTS','DOTS_PROFILE','XDG_STATE_HOME','HOME'):
                try: line=server.read('show-environment','-g',name).strip()
                except ValueError: continue
                if line.startswith(name+'='): env[name]=line[len(name)+1:]
            observed_state=Path(env['XDG_STATE_HOME']) if env.get('XDG_STATE_HOME') else Path(env['HOME'])/'.local/state' if env.get('HOME') else None
            if (Path(env.get('DOTS','')).resolve()!=root or env.get('DOTS_PROFILE')!=selected['current'] or
                    observed_state is None or observed_state.resolve()/'dots'!=state):
                raise ValueError('checkout, profile or state could not be verified')
            if socket_key(socket)!=key: raise ValueError('server identity changed')
            good.append((server,key))
        except (OSError,ValueError,subprocess.TimeoutExpired):
            skipped.append(dict(app='tmux',target=socket,status='pending',reason='server ownership or identity unverified'))
    return good,skipped


def reload_consumers(root, selected, state, generation, changed):
    results=[]
    if 'cli' in changed: results.append(dict(app='cli',status='next invocation'))
    if set(changed)&{'cli','fzf','gum'}: results.append(dict(app='shell',status='next prompt'))
    if 'tmux' in changed:
        from codex_attention import socket_key
        servers,skipped=tmux_servers(root,selected,state);results+=skipped
        if not servers and not skipped: results.append(dict(app='tmux',status='unavailable'))
        for server,key in servers:
            try:
                server.verify()
                if socket_key(server.socket)!=key: raise ValueError('server identity changed')
                result=subprocess.run(server.command('source-file',str(generation/'tmux.visual.conf')),capture_output=True,timeout=5)
                if result.returncode: raise ValueError('tmux refresh failed')
                results.append(dict(app='tmux',target=server.socket,status='notified'))
            except (OSError,ValueError,subprocess.TimeoutExpired): results.append(dict(app='tmux',target=server.socket,status='failed'))
    if 'yazi' in changed:
        ya=shutil.which('ya')
        if not ya: results.append(dict(app='yazi',status='unavailable'))
        else:
            try:
                result=subprocess.run([ya,'pub-to','0','dots-theme-changed','--str',str(state)],capture_output=True,timeout=5)
                results.append(dict(app='yazi',status='notified' if result.returncode==0 else 'failed'))
            except (OSError,subprocess.TimeoutExpired): results.append(dict(app='yazi',status='failed'))
    if 'gitmux' in changed: results.append(dict(app='gitmux',status='next status read'))
    if 'nvim' in changed:results.append(dict(app='nvim',status='next focus or :DotsThemeReload'))
    if 'starship' in changed:
        try:
            # Existing first-party literal adapter only; no plugin dispatcher/hooks.
            sys.path.insert(0,str(LIB/'themes'))
            import starship
            import tomllib
            guards={}
            current,saved,storage=starship.paths(guards)
            with starship.blastoff_locks(current,storage):
                operations=[]
                for path in dict.fromkeys((current,saved)):
                    guards[str(path)]=digest(path)
                    if not path.is_file(): continue
                    original=path.read_bytes()
                    if tomllib.loads(original.decode('utf-8-sig')).get('palette')!='dots': continue
                    updated=starship.update_symbols(original,read_json(generation/'preferences.json'))
                    if updated!=original: operations.append(dict(path=str(path),text=updated.decode('utf-8')))
                result=Store(state).apply('config-refresh-starship',operations,guards,retain=True)
            results.append(dict(app='starship',status='next prompt' if operations else 'unchanged',transaction=result.get('id')))
        except (OSError,ValueError): results.append(dict(app='starship',status='failed'))
    return results


def refresh(root=None, *, dry=False, before=None, retry=True):
    root=checkout(root);selected=context(root);state=state_root();style=Styles(root,selected)
    generation=active(state)
    if generation is None: return dict(schema=1,status='pending',reason='No published theme; CLI values apply on the next invocation',consumers=[])
    palette=read_json(generation/'palette.json')['colors']
    desired=snapshot(palette,root);old=read_json(generation/'preferences.json')
    changed=affected(old,desired)
    if before is not None:
        semantic_changes=affected(before,effective(root))
        if not semantic_changes: return dict(schema=1,status='unchanged',consumers=[])
    templates=[root/'default/themed'/name for name in ('tmux.conf.tpl','fzf.sh.tpl','gum_env.sh.tpl')]
    inputs=[*style.paths,*[Path(x['root'])/'profile.json' for x in selected['layers']],*templates,
            root/'config/tmux/tmux.conf',root/'default/config.json',LIB/'config_values.py',LIB/'tmux_config.py',LIB/'fzf_config.py',LIB/'style_config.py',LIB/'style_catalog.py',LIB/'theme_styles.py',Path(__file__),root/'config/gitmux/gitmux.conf']
    guards={str(p):digest(p) for p in inputs}
    stamp=hashlib.sha256(json.dumps({str(p):guards[str(p)] for p in inputs if p not in style.paths and p.name!='profile.json'},sort_keys=True).encode()).hexdigest()
    metadata=generation/'visual.json'
    prior=read_json(metadata) if metadata.is_file() else {}
    if prior.get('inputs')!=stamp: changed=list(APPS)
    if dry: return dict(schema=1,status='preview',theme=(generation/'id').read_text().strip(),consumers=changed,
                        publication=bool(changed),reason='Refresh supported visuals in the current theme')
    transaction=None
    if changed:
        pointer=state/'current/theme';token=state/'themes/current'
        guards.update({str(p):digest(p) for p in (pointer,token,generation)})
        destination=state/'themes/generations'/('g.'+uuid.uuid4().hex);guards[str(destination)]=None
        with tempfile.TemporaryDirectory(prefix='dots-visual-') as temporary:
            out=Path(temporary)/'generation'
            shutil.copytree(generation,out,symlinks=True)
            # Every regenerated target must be regular; never follow a snapshot link.
            for name in ('preferences.json','colors.json','colors.lua','gitmux.conf','tmux.conf','tmux.visual.conf','fzf.sh','gum_env.sh','yazi.toml','yazi/flavor.toml','visual.tsv','visual.json','status'):
                path=out/name
                if path.is_symlink() or any(p.is_symlink() for p in path.parents if p.is_relative_to(out)):
                    raise ValueError('unsafe generated visual artifact: '+name)
            render_visual(out,root,palette,desired,changed)
            (out/'visual.json').write_text(json.dumps(dict(schema=1,inputs=stamp,checkout=str(root),profile=selected['current']))+'\n')
            operations=[dict(path=str(destination),source=str(out)),dict(path=str(token),text=destination.name+'\n'),
                        dict(path=str(pointer),link=str(destination),directory=True)]
            applied=Store(state).apply('config-refresh',operations,guards,retain=True)
            transaction=applied['id'];generation=destination
    targets=changed or list(APPS) if retry else changed
    results=[]
    if targets:
        try:
            with Store(state).publication_locked([dict(path=str(state/'current/theme'))]):
                if active(state)!=generation: raise ValueError('publication changed before notification; retry')
                results=reload_consumers(root,selected,state,generation,targets)
        except (OSError,ValueError) as error:
            results=[dict(app='refresh',status='failed',reason=str(error))]
    return dict(schema=1,status='pending' if any(r['status'] in ('failed','pending') for r in results) else 'complete' if targets else 'unchanged',
                transaction=transaction,generation=generation.name,consumers=results)


def after_save(root, before):
    try:
        after = effective(root)
        changed=affected(before,after)
        old_cli=before.get('apps',{}).get('cli',{})
        new_cli=after.get('apps',{}).get('cli',{})
        def without_font_styles(doc):
            return dict(doc,colors={k:v for k,v in doc.get('colors',{}).items() if not k.startswith('fonts.') and k!='icons.menu.fonts'},
                        icons={k:v for k,v in doc.get('icons',{}).items() if k!='menu.fonts'})
        if changed==['cli'] and without_font_styles(old_cli)==without_font_styles(new_cli):
            return dict(schema=1,status='complete',consumers=[dict(app='fonts',status='next invocation or popup')])
        def without_wiki_styles(doc):
            return dict(doc,colors={k:v for k,v in doc.get('colors',{}).items() if not k.startswith('wiki.') and k!='icons.menu.wiki'},
                        icons={k:v for k,v in doc.get('icons',{}).items() if k!='menu.wiki'})
        if changed==['cli'] and without_wiki_styles(old_cli)==without_wiki_styles(new_cli):
            return dict(schema=1,status='complete',consumers=[dict(app='wiki',status='next invocation or popup')])
        if (changed==['cli'] and
                {k:v for k,v in old_cli.items() if k!='options'}=={k:v for k,v in new_cli.items() if k!='options'} and
                {k:v for k,v in old_cli.get('options',{}).items() if k!='logo_gradient'}==
                {k:v for k,v in new_cli.get('options',{}).items() if k!='logo_gradient'}):
            return dict(schema=1,status='complete',consumers=[dict(app='cli',status='next invocation')])
        old_format=old_cli.get('formatting',{})
        new_format=new_cli.get('formatting',{})
        formats={key for key in old_format.keys()|new_format.keys() if old_format.get(key)!=new_format.get(key)}
        if (changed==['cli'] and formats and formats<={'cli','menu','wiki'} and
                {k:v for k,v in old_cli.items() if k!='formatting'}=={k:v for k,v in new_cli.items() if k!='formatting'}):
            return dict(schema=1,status='complete',consumers=[dict(app=key,status='next popup' if key=='menu' else 'next invocation') for key in sorted(formats)])
        if not changed:
            if before.get('config',{}).get('apps',{}).get('wiki') != after.get('config',{}).get('apps',{}).get('wiki'):
                return dict(schema=1,status='complete',consumers=[dict(app='wiki',status='next invocation or popup')])
            if before.get('config',{}).get('apps',{}).get('fonts') != after.get('config',{}).get('apps',{}).get('fonts'):
                return dict(schema=1,status='complete',consumers=[dict(app='fonts',status='next invocation or popup')])
            if before.get('config',{}).get('apps',{}).get('setup') != after.get('config',{}).get('apps',{}).get('setup'):
                return dict(schema=1,status='complete',consumers=[dict(app='setup',status='next invocation')])
            if before.get('config',{}).get('apps',{}).get('menu') != after.get('config',{}).get('apps',{}).get('menu'):
                return dict(schema=1,status='complete',consumers=[dict(app='menu',status='next popup')])
            return dict(schema=1,status='unchanged',consumers=[])
        return refresh(root,before=before,retry=False)
    except (OSError,ValueError,KeyError,TypeError) as error:
        return dict(schema=1,status='failed',reason=str(error),consumers=[],retry='dots config refresh')


def preview_save(root, plan):
    style = Styles(root)
    from config_cli import ControlPlan
    if isinstance(plan,ControlPlan):
        from config_values import Controls
        values=Controls(root,replacements={plan.path:plan.data}).values
        before=snapshot(style.palette,root)
        after=snapshot(style.palette,root,controls=values)
        changes=affected(before,after)
        if before['config'].get('apps',{}).get('fonts') != after['config'].get('apps',{}).get('fonts'):
            changes.append('fonts')
        if before['config'].get('apps',{}).get('menu') != after['config'].get('apps',{}).get('menu'):
            changes.append('menu')
        if before['config'].get('apps',{}).get('setup') != after['config'].get('apps',{}).get('setup'):
            changes.append('setup')
        return dict(schema=1,status='preview',consumers=changes,reason='Refresh affected active consumers after saving' if changes else 'No active consumer change')
    proposed = Styles(root, replacements={plan.path: plan.data}, palette=style.palette)
    changes = affected(snapshot(style.palette, root, styles=style), snapshot(style.palette, root, styles=proposed))
    return dict(schema=1,status='preview', consumers=changes, reason='Refresh affected active visuals after saving' if changes else 'No active visual change')
