"""Compile literal component preferences into owned tmux options."""
import re

ATTRS={'bold':'bold','dim':'dim','italic':'italics','underline':'underscore','reverse':'reverse','strikethrough':'strikethrough'}
STATES=('active','inactive','alert')
SPANS=('number','icon','name','surround','spacer')
ROLES={'session','session.repository','clock.icon','clock.text','clock.surround','clock.spacer','git.surround'}
ROLES.update('battery.'+part for part in ('icon','text','surround','spacer'))
ROLES.update('battery.'+state+'.'+part for state in ('critical','low','normal','charging','unknown') for part in ('icon','text'))
for component,states,spans in (('tabs',STATES,('number','icon','surround','spacer')),
                               ('session',STATES,SPANS),('window',('active','inactive','attention'),SPANS)):
    ROLES.update(component+'.'+part for part in spans)
    ROLES.update(component+'.'+state+suffix for state in states for suffix in ('',*('.'+part for part in spans)))
ROLES.update('indicators.'+name+suffix for name in ('copy','prefix','zoom','working','waiting','attention') for suffix in ('','.surround','.spacer'))
ROLES.update('hosts.'+host for host in ('github','gitlab','bitbucket'))
ICONS={'clock.fixed','clock.day','clock.night','clock.unknown','session.default','window.default'}
ICONS.update('battery.'+state for state in ('critical','low','normal','charging','unknown'))


def literal(text):
    return str(text).replace('#','##')


def quote(text):
    return "'"+text.replace("'","'\\''")+"'"


def tmux_color(styles,value,background=False):
    from style_config import ALIASES
    value=styles.color(value,'default' if background else 'foreground')
    value=ALIASES.get(value,value)
    return {'foreground':'default','background':'default','reset':'default','muted':'brightblack','bright_foreground':'brightwhite'}.get(value,value.replace('bright_','bright'))


def style(styles,role,fallback='',fields=None):
    result=[]
    for field,value in styles.style(role,app='tmux').items():
        if fields is not None and field not in fields:continue
        if field in ('fg','bg'):result.append(field+'='+tmux_color(styles,value,field=='bg'))
        elif field in ATTRS:result.append(('' if value else 'no')+ATTRS[field])
    return fallback+('#['+','.join(result)+']' if result else '')


def compile_options(root,selected,source,styles=None):
    from config_values import Controls
    from style_config import Styles
    styles=styles or Styles(root,selected)
    values=Controls(root,selected).values
    cfg=values.get('apps',{}).get('tmux',{})
    fmt=values.get('formatting',{}).get('apps',{}).get('tmux',{})
    original={m[1]:m[2] for line in source.splitlines() if (m:=re.fullmatch(r"\s*set -g ([^ ]+) '(.*)'",line))}
    options={}
    def stored(text):
        key='@dots-config-fragment-'+str(sum(k.startswith('@dots-config-fragment-') for k in options))
        options[key]=text
        return '#{E:'+key+'}'
    def choice(predicate,yes,no=''):
        return '#{?'+predicate+','+stored(yes)+','+stored(no)+'}'
    def lit(text):
        # The value is expanded after the enclosing conditional is parsed.
        # Commas, braces and #() in user text cannot become format syntax.
        key='@dots-config-literal-'+str(sum(k.startswith('@dots-config-literal-') for k in options))
        options[key]=literal(text)
        return '#{'+key+'}'
    def state_style(role,base=''):
        generic=style(styles,role,base)
        if role.startswith('window.') and role.split('.')[1] in SPANS:
            part=role.split('.')[1]
            variants=[style(styles,'window.'+state+'.'+part,generic) for state in ('attention','active','inactive')]
            if variants!=[generic]*3:return choice('#{E:@dots-window-alert}',variants[0],choice('window_active',variants[1],variants[2]))
        if role.startswith('session.') and role.split('.')[1] in SPANS:
            return style(styles,'session.active.'+role.split('.')[1],generic)
        return generic
    def span(role,text,base=''):
        selected_style=state_style(role,base)
        return stored('#[default]'+selected_style+text+'#[default]'+base) if selected_style!=base else text
    def surround(component,text,state=None,base=None):
        data=fmt.get(component,{})
        if state:data=dict(data,**data.get(state,{}))
        base=base or ('#{E:@dots-window-style}' if component=='windows' else '#{E:@dots-session-style}' if component=='session' else '#[default]')
        role=('window' if component=='windows' else component)
        return span(role+'.surround',lit(data.get('before',' ')),base)+text+span(role+'.surround',lit(data.get('after',' ')),base)
    def part(component,name,text,base):
        data=fmt.get(component,{}).get(name,{})
        role=('window' if component=='windows' else component)+'.'+name
        return span(role,lit(data.get('before',''))+text+lit(data.get('after','')),base)
    def color(role,default):return tmux_color(styles,styles.style(role,app='tmux').get('fg',default))
    def indicator(name,text,base,restore='#[default]'):
        data=fmt.get('indicators',{}).get(name,{})
        base=style(styles,'indicators.'+name,base)
        return (base+span('indicators.'+name+'.surround',lit(data.get('before','')),base)+text+
                span('indicators.'+name+'.surround',lit(data.get('after','')),base)+
                span('indicators.'+name+'.spacer',lit(data.get('spacer','')),base)+restore)
    for state in ('working','waiting','attention'):
        base=style(styles,'status.'+state) if state!='attention' else ''
        base=style(styles,'icons.status.'+state,base) if state!='attention' else base
        text=cfg.get('indicators',{}).get(state,{}).get('text')
        glyph=lit(text) if text is not None else '#{@dots-icon-status-'+state+'}' if state!='attention' else ''
        options['@dots-marker-'+state]=(choice('#{E:@dots-window-alert}',
            indicator('attention',glyph,'#{E:@dots-window-alert-style}','#{E:@dots-window-style}'),
            indicator(state,glyph,base,'#{E:@dots-window-style}')) if glyph else '')
    marker='#{?#{E:@dots-window-codex-working},#{E:@dots-marker-working},#{?#{E:@dots-window-codex-waiting},#{E:@dots-marker-waiting},}}'
    if cfg.get('indicators',{}).get('attention',{}).get('text') is not None:
        marker='#{?#{E:@dots-window-codex-attention},#{E:@dots-marker-attention},'+marker+'}'
    options['@dots-window-marker']=marker
    clock=cfg.get('clock',{});mode=clock.get('icon_mode','none');icon=''
    if mode=='fixed':icon=lit(styles.icon('clock.fixed','',app='tmux'))
    elif mode=='daylight':
        icons=[lit(styles.icon('clock.'+state,'',app='tmux')) for state in ('day','night','unknown')]
        icon='#{?#{==:#{E:@dots-termux-daylight},day},'+icons[0]+',#{?#{==:#{E:@dots-termux-daylight},night},'+icons[1]+','+icons[2]+'}}'
    options['@dots-termux-daylight-fg']='#{?#{==:#{E:@dots-termux-daylight},day},'+color('daylight.day','yellow')+',#{?#{==:#{E:@dots-termux-daylight},night},'+color('daylight.night','blue')+',#{@dots-termux-fg}}}'
    clockbase='#[bold,bg=#{@dots-termux-clock-bg},fg=#{E:@dots-termux-daylight-fg}]'
    options['@dots-config-clock-time']=literal(literal(fmt.get('clock',{}).get('format','%-I:%M')))
    time=span('clock.text','#{T:@dots-config-clock-time}',clockbase)
    icontext=span('clock.icon',icon,clockbase)+choice('#{!=:'+icon+',}',span('clock.spacer',lit(fmt.get('clock',{}).get('spacer',' ')),clockbase)) if icon else ''
    options['@dots-config-clock']=clockbase+surround('clock',icontext+time,base=clockbase)+'#[default]'
    indicators=[]
    for name,predicate,fg in (('copy','pane_in_mode','indicator'),('prefix','client_prefix','prefix'),('zoom','window_zoomed_flag','indicator')):
        base='#[fg=#{@dots-'+fg+'-fg},bg=#{@dots-'+fg+'-bg},bold]'
        body=indicator(name,lit(cfg.get('indicators',{}).get(name,{}).get('text',name.upper())),base)
        indicators.append(choice(predicate,body))
    options['status-right']=''.join(indicators)
    for state,option in (('active','selected'),('inactive','idle'),('attention','alert')):
        key='@dots-window-'+option+'-style'
        # The theme template already binds state fg/bg to native options. Keep
        # its working/Codex contrast conditions; add nullable attributes here.
        options[key]=style(styles,'window.'+state,original.get(key,''),fields=ATTRS)
    for partname,option in (('number','@dots-window-number-style'),('name','@dots-window-name-style')):
        options[option]=state_style('window.'+partname,original.get(option,''))
    windowbase='#{E:@dots-window-style}'
    options['@dots-window-styled-prefix']=original.get('@dots-window-styled-prefix','').replace('#{E:@dots-window-number-style}#{E:@dots-window-number}','#{E:@dots-window-number-style}'+part('windows','number','#{E:@dots-window-number}',windowbase))
    label=original.get('@dots-window-styled-label','').replace('#{E:@dots-window-name}#{E:@dots-window-style}',part('windows','name','#{E:@dots-window-name}',windowbase)+windowbase)
    spacer=span('window.spacer',lit(fmt.get('windows',{}).get('spacer',' ')),windowbase)
    # The default native label separator is already a configurable icon.
    if fmt.get('windows',{}).get('spacer',' ')!=' ':label=label.replace('#{E:@dots-label-separator}',spacer)
    else:label=label.replace('#{E:@dots-label-separator}',span('window.spacer','#{E:@dots-label-separator}',windowbase))
    window_icon=styles.icon('window.default','',app='tmux')
    if window_icon:label=part('windows','icon',lit(window_icon),windowbase)+spacer+label
    options['@dots-window-styled-label']=label
    alertlabel='#{?#{!=:#{E:@dots-window-label},},#{E:@dots-window-styled-label},#{q/h:window_name}}'
    # Preserve the uniform attention label until a span is explicitly customized.
    if not any(styles.style('window.'+state+'.'+part,app='tmux') or styles.style('window.'+part,app='tmux') for state in ('attention',) for part in SPANS) and not window_icon:
        alertlabel='#{?#{!=:#{E:@dots-window-label},},#{?#{E:@dots-window-codex-attention},#{E:@dots-window-label},#{E:@dots-window-styled-label}},#{q/h:window_name}}'
    options['@dots-window-format']=choice('#{E:@dots-windows-visible}',windowbase+choice('#{E:@dots-window-alert}',surround('windows',alertlabel,'alert'),surround('windows','#{E:@dots-window-styled-label}'))+'#[default]')
    options['window-status-separator']=state_style('window.spacer','#[fg=#{@dots-separator-fg},bg=#{@dots-separator-bg},nobold,nounderscore,noreverse,nodim]')+lit(fmt.get('windows',{}).get('separator','│'))+'#[default]'
    session=cfg.get('session',{});sessionbase='#{E:@dots-session-style}'
    options['@dots-session-style']=style(styles,'session.active',style(styles,'session',original.get('@dots-session-style','')))
    # Keep the native width accounting and empty-name suppression.
    options['@dots-session-visible-number']='#{@dots-session-number}' if session.get('show_number',True) else ''
    for key in ('@dots-session-prefix-width','@dots-session-has-separator','@dots-session-body-label','@dots-session-visible'):
        options[key]=original.get(key,'').replace('#{E:@dots-session-number}','#{E:@dots-session-visible-number}').replace('#{@dots-session-number}','#{E:@dots-session-visible-number}')
    name=original.get('@dots-session-name','')
    if session.get('name_source')=='session':name='#{=/#{E:@dots-session-name-width}/;q/h:session_name}'
    elif session.get('name_source')=='repository':name='#{?#{!=:#{@dots-workspace-repository-name},},#{=/#{E:@dots-session-name-width}/;q/h:@dots-workspace-repository-name},#{=/#{E:@dots-session-name-width}/;q/h:session_name}}'
    if not session.get('show_name',True):name=''
    repo_style=style(styles,'session.repository',sessionbase) if session.get('repository_color',False) else sessionbase
    for host in ('github','gitlab','bitbucket') if session.get('repository_color',False) else ():
        host_style=style(styles,'hosts.'+host,repo_style)
        if host_style!=repo_style:repo_style=choice('#{==:#{@dots-workspace-repository-host},'+host+'}',host_style,repo_style)
    if session.get('repository_color',False):repo_style=choice('#{||:#{!=:#{@dots-workspace-repository-name},},#{!=:#{E:@dots-remote-icon},}}',repo_style,sessionbase)
    options['@dots-session-name']=name
    options['@dots-session-icon']=original.get('@dots-session-icon','')
    override=styles.resolve('icons','session.default','tmux')
    if override['source'] or not session.get('repository_icon',True):options['@dots-session-icon']=lit(override['value'] or '')
    text=original.get('@dots-session-text','').replace('#{E:@dots-session-number}',part('session','number','#{E:@dots-session-visible-number}',sessionbase))
    text=text.replace('#{E:@dots-session-icon}',stored(repo_style+part('session','icon','#{E:@dots-session-icon}',repo_style)+sessionbase),1)
    text=text.replace('#{?#{!=:#{E:@dots-session-name},},#{E:@dots-session-name},}',
        choice('#{!=:#{E:@dots-session-name},}',repo_style+part('session','name','#{E:@dots-session-name}',repo_style)+sessionbase))
    spacer=span('session.spacer',lit(fmt.get('session',{}).get('spacer',' ')),sessionbase)
    text=text.replace(', ,}',','+spacer+',}')
    separator=span('session.spacer','#{E:@dots-label-separator}',sessionbase) if fmt.get('session',{}).get('spacer',' ')==' ' else spacer
    text=text.replace('#{E:@dots-label-separator}',separator)
    options['@dots-session-text']=text
    options['status-left']=choice('#{E:@dots-session-visible}',sessionbase+surround('session','#{E:@dots-session-text}')+'#[default]#{?#{E:@dots-windows-visible},#{E:@dots-status-separator},}')
    if session.get('multiple',False):
        options['status-left']='#(python3 -B "${XDG_CONFIG_HOME:-$HOME/.config}/tmux/session-status.py" --socket #{q:socket_path} --current #{q:session_id} --width #{q:@dots-session-width} 2>/dev/null || printf "\\n")'
    gitbase=style(styles,'git')
    content=surround('git','#{=/#{e|-:#{E:@dots-gitmux-width},1}/…:#{E:@dots-gitmux}}',base=gitbase or '#[default]')
    options['@dots-gitmux-segment']='#[nolist align=left norange default]'+choice('#{!=:#{E:@dots-gitmux},}','#{?#{E:@dots-gitmux-preceded},#{E:@dots-status-separator},}'+gitbase+'#[push-default]'+content+'#[pop-default]#[default]')
    return options


def fragment(root,selected,source,styles=None):
    return '\n'.join('set -g '+key+' '+quote(value) for key,value in compile_options(root,selected,source,styles).items())+'\n'
