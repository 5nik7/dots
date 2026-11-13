"""Human Config listing; structured/scalar and redirected reports stay separate."""
import copy
import json
from dataclasses import dataclass

from resources import cells
from style_config import ATTRS


@dataclass(frozen=True)
class Glyph:
    text: str
    code: str
    annotation: str


@dataclass(frozen=True)
class StyleRecord:
    text: str
    code: str
    children: dict
    annotation: str = ''


def scalar(value):
    if value is True:return 'yes'
    if value is False:return 'no'
    if value is None:return 'not set'
    if value=='':return '(empty)'
    if isinstance(value,list):return json.dumps(value,ensure_ascii=False)
    return str(value)


def style_label(value):
    if not isinstance(value,dict):return 'default' if value is None or value=='' else str(value)
    parts=[]
    for key,item in value.items():
        parts.append(key if item is True else key+':false' if item is False else key+':'+('null' if item is None else str(item)))
    return ','.join(parts) or 'default'


def compact_styles(values,styles,path=(),_help=None):
    _help={} if _help is None else _help
    result={}
    for key,value in values.items():
        if not isinstance(value,dict):result[key]=value;continue
        fields={name:value[name] for name in ('fg','bg','sp',*ATTRS) if name in value and not isinstance(value[name],dict)}
        children=compact_styles({name:item for name,item in value.items() if name not in fields},styles,(*path,key),_help)
        if fields:
            # Resolve saved symbolic/missing-palette references through the same
            # inheritance path as consumers, while displaying the saved names.
            effective=styles.style('.'.join((*path,key)),fields)
            if (*path,key)[:3]==('apps','cli','help') and len((*path,key))==4:
                if 'styles' not in _help:
                    from help_presentation import HelpStyles
                    _help['styles']=HelpStyles(styles=styles)
                effective=_help['styles'].style(key)
            code=styles.sgr_fields({name:item for name,item in effective.items() if item is not None})
            label=style_label(fields);annotation=''
            if '.'.join((*path,key)).startswith('apps.menu.popup') and any(v is None for v in fields.values()):
                label=style_label({k:'inherited' if v is None else v for k,v in fields.items()})
                annotation='lib/dots/interaction.py (caller/FZF palette)'
            result[key]=StyleRecord(label,'0;'+code,children,annotation)
        else:result[key]=children
    return result


def icon_sample(styles,key,glyph,tmux_options=None,*,published=None,menu_formatting=None,weather=None):
    from config_keys import canonical
    from style_catalog import split
    from config_icon_samples import menu_entry
    app,role=split(key)
    app=app or 'cli'
    if app=='cli' and role=='navigation.codex':role='applications.codex'
    roles=['ui.foreground','icons.'+role];state=''
    doc={'fg':'foreground'}
    entry=menu_entry(role) if app=='cli' else None
    fields=styles.style('icons.'+role,app='cli') if role.startswith(('files.','hosts.')) or role=='git.branch' else {}
    native=published.sample(role,fields=tuple(k for k in ('fg','bg') if fields.get(k) is None)) if published and app=='cli' and not entry else None
    if native:
        # Presentation.paint inserts CLI icon overrides into the native span;
        # a background-only override retains its file/identity foreground.
        code='0;'+native[0]
        annotations=[native[1]] if native[1] else []
        if fields:
            code+=';'+styles.sgr_fields({k:v for k,v in fields.items() if v is not None})
            for field in ('fg','bg'):
                resolved=styles.resolve('colors','icons.'+role+'.'+field,'cli')
                if fields.get(field) is not None and resolved['declarations']:
                    annotations.append(canonical(resolved['declarations'][-1]['key']))
        return Glyph(glyph,code,', '.join(annotations))
    if app=='cli' and (role.startswith('menu.') or entry):
        # Match menus.entry_spans: the shared menu icon style, then a
        # role-specific override. ui.foreground is not this consumer's color.
        roles=['menu.icon']+(['icons.'+role] if not entry or entry[1] else [])
        doc={}
        if entry:state='menu'
    elif app=='cli' and role in ('status.error','status.success','status.warning','status.info'):
        roles=[role if role!='status.info' else 'ui.label','icons.'+role]
        state='file status' if role=='status.info' else ''
    elif app=='cli' and role=='navigation.project':
        roles=['ui.accent','icons.'+role];doc['bold']=True;state='session browser, noncurrent project'
    elif app=='cli' and role.startswith('weather.') and role.split('.')[1] in ('humidity','precip','sunrise','sunset'):
        name=role.split('.')[1]
        configured=(weather or {}).get('icon_colors',{})
        rows=weather_icons({'icons':{name:glyph},'icon_colors':configured},styles)
        sample=rows[0][1][name]
        annotation='apps.wttr.icon_colors.'+name if name in configured else sample.annotation
        return Glyph(glyph,sample.code,annotation+' (wttr fallback glyph)')
    elif app=='tmux' or app=='cli' and role in ('status.working','status.waiting','git.stashed','navigation.separator'):
        app='tmux'
        # These glyphs have component styles, rather than colors.icons.*. Use
        # the declared clock/battery state and an explicit active-state sample
        # for session/window glyphs; no live tmux or provider reads are needed.
        if role.startswith('clock.'):
            state=role.split('.')[1]
            roles=['ui.foreground',*(['daylight.'+state] if state in ('day','night') else []),'clock.icon']
            doc['bold']=True;state=''
        elif role.startswith('battery.'):
            roles=['ui.foreground',role,'battery.icon',role+'.icon']
        elif role=='window.default':
            roles=['ui.foreground','window.active','window.icon','window.active.icon'];state='active'
        elif role=='session.default' or role.startswith('hosts.') or role=='git.repository':
            roles=['ui.foreground','session','session.active'];state='active'
            if (tmux_options or {}).get('session',{}).get('repository_color'):
                roles+=['session.repository']
                if role.startswith('hosts.'):roles.append(role)
            roles+=['session.icon','session.active.icon']
        elif role in ('status.working','status.waiting'):
            roles=['ui.foreground',role,'icons.'+role,'indicators.'+role.split('.')[1]]
            state='tmux indicator'
        elif role=='git.stashed':
            # Gitmux consumes only the generated foreground token here.
            color=styles.style('ui.muted',app='tmux').get('fg','muted')
            source=styles.resolve('colors','ui.muted.fg','tmux')
            return Glyph(glyph,'0;'+styles.sgr_fields({'fg':color}),
                         (canonical(source['declarations'][-1]['key']) if source['declarations'] else 'muted')+' (Gitmux)')
        elif role=='navigation.separator':
            color=styles.style('ui.separator',app='tmux').get('fg','muted')
            source=styles.resolve('colors','ui.separator.fg','tmux')
            return Glyph(glyph,'0;'+styles.sgr_fields({'fg':color,'bg':'dark_background'}),
                         (canonical(source['declarations'][-1]['key']) if source['declarations'] else 'muted')+', dark_background (tmux status separator)')
    sources={}
    for name in roles:
        doc=styles.style(name,doc,app=app)
        for field in ('fg','bg'):
            resolved=styles.resolve('colors',name+'.'+field,app)
            if name!='ui.foreground' and resolved['declarations']:
                if doc.get(field) is None:sources.pop(field,None)
                else:sources[field]=canonical(resolved['declarations'][-1]['key'])
    if entry:
        overrides=(menu_formatting or {}).get('entries',{}).get(entry[0],{}).get('icon',{})
        for field,value in overrides.items():
            if value is None:continue
            doc[field]=value
            if field in ('fg','bg'):
                sources[field]='formatting.apps.menu.entries['+json.dumps(entry[0])+'].icon.'+field
    annotation=', '.join(sources.values())
    if state:annotation+=(' ' if annotation else '')+'('+state+')'
    return Glyph(glyph,'0;'+styles.sgr_fields({key:value for key,value in doc.items() if value is not None}),
                 annotation)


def icon_tree(values,styles,path=(),tmux_options=None,**kwargs):
    return {key:icon_tree(value,styles,(*path,key),tmux_options,**kwargs) if isinstance(value,dict) else
            icon_sample(styles,'.'.join((*path,key)),value,tmux_options,**kwargs) for key,value in values.items()}


def weather_icons(weather,styles):
    from config_values import name
    from wttr.styling import Colors,DETAIL_COLORS
    native=Colors();native.palette=styles.palette
    result=[]
    for group,color_group,label in (('icons','icon_colors','wttr'),('night_icons','night_icon_colors','wttr night')):
        rows={}
        for key,glyph in weather.get(group,{}).items():
            source=None;code=None
            if key in weather.get(color_group,{}):shade=weather[color_group][key]
            elif key in DETAIL_COLORS and group=='icons':
                if key in ('sunrise','sunset'):
                    resolved=styles.resolve('colors','daylight.'+key+'.fg','wttr')
                    if resolved['declarations']:
                        source=resolved['declarations'][-1]['key']
                        shade=styles.style('daylight.'+key,app='wttr')['fg']
                        code=styles.sgr_fields({'fg':shade})
                    else:shade=DETAIL_COLORS[key]
                else:shade=DETAIL_COLORS[key]
            else:
                target=key if key in weather.get('icon_colors',{}) else 'unknown'
                shade=weather.get('icon_colors',{}).get(target,'default')
                if target in weather.get('icon_colors',{}):source=name(('apps','wttr','icon_colors',target))
            rows[key]=Glyph(glyph,'0;'+(code or native.sgr(shade) or '39'),source or style_label(shade))
        if rows:result.append((label,rows))
    return result


def tree(ui,values,depth=0):
    """Indent structural children; align siblings without flattening their keys."""
    indent=ui.detail_indent+2*depth
    labels=[str(key) for key,value in values.items() if not isinstance(value,dict)]
    from row_layout import width
    configured=width(ui.formatting.get('label_width',0),ui.width,indent=indent,gap=ui.formatting.get('label_gap',1))
    label_width=max([0,*[cells(label)+2 for label in labels]]) if ui._config_tree_auto_columns else configured
    for key,value in values.items():
        label='‒ '+str(key)
        if isinstance(value,dict):
            ui.detail_spans(label,[],indent=indent,label_width=0)
            if value:tree(ui,value,depth+1)
            else:ui.detail_spans('‒', [('No configured values','90')],indent=indent+2,label_width=0)
        else:
            spans=([(value.text or '(empty)',value.code)]+([('  '+ui.path(value.annotation),'90')] if value.annotation else []) if isinstance(value,Glyph) else
                   [(value.text,value.code)]+([('  '+ui.path(value.annotation),'90')] if value.annotation else []) if isinstance(value,StyleRecord) else [(scalar(value),None)])
            ui.detail_spans(label,spans,indent=indent,label_width=label_width)
            if isinstance(value,StyleRecord) and value.children:tree(ui,value.children,depth+1)


def listing(ui,result):
    # Samples are keyed by configuration identity, not glyph identity: the same
    # glyph may occur in multiple roles with different colors. Suppress only the
    # shared renderer's automatic glyph substitution for this report.
    missing=object();previous=getattr(ui,'_icon_paints',missing)
    ui._icon_paints={}
    try:_listing(ui,result)
    finally:
        if previous is missing:del ui._icon_paints
        else:ui._icon_paints=previous


def _listing(ui,result):
    config=copy.deepcopy(result['config'])
    from config_values import current
    controls=current()
    from style_config import Styles
    from profile_config import context
    defaults=result['profile']=='defaults'
    styles=Styles(controls.root,context(controls.root,None if defaults else result['profile']),defaults=defaults)
    from config_fallbacks import Fallbacks
    fallbacks=Fallbacks(styles,config)
    try:columns=controls.resolve('formatting.apps.cli.label_width')
    except ValueError:columns={}
    # The stock detail width is too short for settings names. Align siblings by
    # default, but keep every explicit profile/shared column customization.
    ui._config_tree_auto_columns=(not ui.formatting or ui.formatting.get('label_width')==10 and columns.get('value')==10 and
                                 columns.get('source')==str(controls.root/'default/config.json'))
    ui.heading('Dots config')
    alias=config.get('profile',{}).get('alias')
    ui.detail_spans('Profile',[(result['profile']+(' ('+alias+')' if alias else ''),'94')],label_width=0)
    ui.resource_detail('‒',result['path'],label_width=1)
    categories=result.get('categories') or ('files','settings','environment','icons','colors','formatting','apps')
    weather=config.get('apps',{}).get('wttr',{})
    weather_config=copy.deepcopy(weather)
    weather_rows=weather_icons(weather,styles)
    from config_icon_samples import PublishedSamples
    # A different profile/defaults report must not borrow the active profile's
    # published file rules. Native samples explicitly identify publication.
    active=context(controls.root)
    published=PublishedSamples(styles) if not defaults and styles.selected['layers']==active['layers'] else None
    for name,color_name,label in (('icons','icon_colors','wttr'),('night_icons','night_icon_colors','wttr night')):
        icons=weather.pop(name,{})
        colors=weather.pop(color_name,{})
        # Keep standalone native color overrides visible even without a glyph.
        remaining={key:value for key,value in colors.items() if key not in icons}
        if remaining:weather[color_name]=remaining
    for group in categories:
        entries=config.get(group,{})
        if not entries and not (group=='icons' and weather_rows):continue
        ui.emit();ui.heading(ui.indentation(ui.detail_indent)+group.title())
        if group=='files':entries={owner+'('+str(len(items))+')':'dots config get files.'+owner for owner,items in entries.items()}
        elif group=='colors':entries=compact_styles(entries,styles)
        elif group=='icons':entries=icon_tree(entries,styles,tmux_options=config.get('apps',{}).get('tmux',{}),
                published=published,menu_formatting=config.get('formatting',{}).get('apps',{}).get('menu',{}),weather=weather_config)
        elif group in ('apps','formatting'):entries=fallbacks.tree(entries,(group,))
        tree(ui,entries)
        if group=='icons':
            for label,values in weather_rows:
                ui.detail_spans('‒ '+label,[('apps.wttr.'+('night_icons' if label.endswith('night') else 'icons'),'90')],label_width=0)
                tree(ui,values,1)
