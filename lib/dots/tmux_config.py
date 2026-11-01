"""Compile placement of existing owned status components into inert tmux formats."""
import re
from config_values import Controls


def row_positions(cfg,platform):
    termux=platform=='termux';count=cfg.get('rows',0) or (2 if termux else 1)
    main=cfg.get('main_row');main=(1 if termux and count==2 else 0) if main is None else main
    upper=cfg.get('termux_row');upper=(1-main if count==2 else 0) if upper is None else upper
    return count,main,upper


def validate_layout(cfg,platform):
    count,main,upper=row_positions(cfg,platform);termux=platform=='termux'
    if main>=count or termux and count==2 and (upper>=count or upper==main):raise ValueError('tmux row placement overlaps or exceeds the configured row count')


def layout(root,selected,styles=None):
    cfg=Controls(root,selected).values.get('formatting',{}).get('apps',{}).get('tmux',{})
    validate_layout(cfg,selected['facts']['platform'])
    source=root/'config/tmux/tmux.conf'
    if not source.is_file():return '# No managed status layout source'
    lines=source.read_text().splitlines()
    def extract(option):
        found=[]
        for line in lines:
            match=re.fullmatch(r"\s*set -g "+re.escape(option)+r" '(.*)'",line)
            if match:found.append(match[1])
        return found
    rows0=extract('status-format[0]');rows1=extract('status-format[1]')
    if len(rows0)<2 or not rows1:return '# No managed status layout source'
    termux=selected['facts']['platform']=='termux'
    defaults={'main_left':['session','windows','git'],'main_right':['indicators'],
              'termux_left':['clock','tabs'],'termux_right':['battery']}
    main=rows1[0] if termux else rows0[0];upper=rows0[1]
    if any(cfg.get(key,default)!=default for key,default in defaults.items()):
        right=upper.split('#[default nobold align=right]',1)[1].removesuffix('#[pop-default]')
        components=dict(session='#{E:status-left}',indicators='#{E:status-right}',
            windows='#{?#{E:@dots-windows-visible},#[list=on]#{W:#[range=window|#{window_index}]#{E:window-status-format}#[norange],#[list=focus range=window|#{window_index}]#{E:window-status-current-format}#[norange list=on]}#[nolist],}',
            git='#{E:@dots-gitmux-segment}',
            clock='#{E:@dots-config-clock}' if termux else '',
            tabs='#{E:@dots-termux-numbers}' if termux else '',battery=right if termux else '')
        def row(which,bg):
            result='#[fill='+bg+',bg='+bg+']#[push-default]'
            for side in ('left','right'):
                result+='#[nolist align='+side+' norange default]'
                result+='#{E:@dots-status-separator}'.join(components[name] for name in cfg.get(which+'_'+side,defaults[which+'_'+side]) if components[name])
            return result+'#[pop-default]'
        main=row('main','#{@dots-termux-lower-bg}' if termux else 'default')
        upper=row('termux','#{@dots-termux-bg}')
    upper=upper.replace('#[align=left,bold,bg=#{@dots-termux-clock-bg},fg=#{E:@dots-termux-daylight-fg}] %-I:%M #[default]', '#[align=left]#{E:@dots-config-clock}')
    count,main_row,upper_row=row_positions(cfg,selected['facts']['platform'])
    if main_row>=count or termux and count==2 and (upper_row>=count or upper_row==main_row):raise ValueError('tmux row placement overlaps or exceeds the configured row count')
    rows=['']*count;rows[main_row]=main
    if termux and count==2:rows[upper_row]=upper
    def literal(value):return "'"+value.replace("'","'\\''")+"'"
    result=['set -g @dots-config-status '+('on' if count==1 else str(count)),
            'set -g @dots-config-platform '+selected['facts']['platform'],
            'set -g @dots-config-position '+cfg.get('position','top')]
    result+=['set -g @dots-config-row'+str(i)+' '+literal(rows[i] if i<len(rows) else '') for i in (0,1)]
    # Existing servers can apply the fragment without sourcing hooks/key bindings.
    result.append("if-shell -F '#{&&:#{!=:#{@dots-tmux-row},},#{||:#{!=:#{@dots-config-platform},termux},#{!=:#{TERMUX_VERSION},}}}' { set -gF status '#{@dots-config-status}' ; set -gF status-position '#{@dots-config-position}' ; set -gF status-format[0] '#{@dots-config-row0}' ; set -gF status-format[1] '#{@dots-config-row1}' }")
    from tmux_controls import fragment
    return fragment(root,selected,source.read_text(),styles)+'\n'.join(result)+'\n'
