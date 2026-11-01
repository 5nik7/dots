"""Human fallback previews for existing Config keys only; no native inventory."""
import os
from pathlib import Path
import re

from resources import read_data


def fzf_values(text):
    """Read the one literal published assignment, never source its shell file."""
    text=text.replace('\\\n','')
    matches=re.findall(r'^\s*export _FZF_COLORS_=(["\'])(.*?)\1\s*$',text,re.M)
    if len(matches)!=1:return {}
    from fzf_config import validate_color
    result={}
    for part in matches[0][1].split(','):
        key,sep,value=part.partition(':')
        if not sep or not re.fullmatch(r'[a-z][a-z+-]*',key):continue
        try:validate_color(value)
        except ValueError:continue
        result[key]=value
    return result


def fzf_sample(styles,key,value,source=''):
    from config_view import Glyph,style_label
    from style_config import ATTRS
    from fzf_config import validate_color
    validate_color(value)
    fields={};flags=[]
    side='bg' if 'bg' in key or key=='gutter' else 'fg'
    for token in value.split(':'):
        if token=='regular':fields.update({attr:False for attr in ATTRS});flags.append(token)
        elif token=='strip':flags.append(token)
        elif token in (*ATTRS,'blink'):fields[token]=True
        elif token.startswith('no') and token[2:] in (*ATTRS,'blink'):fields[token[2:]]=False
        else:fields[side]='default' if token=='-1' else token
    code=[]
    for name,shade in fields.items():
        if name in ('fg','bg'):
            code.append(('48' if name=='bg' else '38')+';5;'+shade if shade.isdigit() else styles.sgr_color(shade,name=='bg'))
        elif name in ATTRS and shade:code.append(str(ATTRS[name]))
    visible={k:v for k,v in fields.items() if v is not False or 'regular' not in flags}
    text=','.join(([style_label(visible)] if visible else [])+flags)
    return Glyph(text or value,'0;'+(';'.join(code) or '39'),source)


class Fallbacks:
    def __init__(self,styles,config):
        from profile_config import context
        self.styles=styles;self.config=config
        self.active=not styles.defaults and styles.selected['layers']==context(styles.root)['layers']
        self._fzf=None
        self._native={}

    def fzf(self):
        if self._fzf is None:
            self._fzf=({},'')
            if self.active:
                from themes.inspection import Inspection
                inspected=Inspection()
                path=(inspected.generation or inspected.active)/'fzf.sh'
                origin=inspected.source('fzf.sh').get('path') if inspected.identity else None
                self._fzf=(fzf_values(read_data(path)),str(origin or path)+' (published; current source)')
        return self._fzf

    def leaf(self,path,value):
        from config_view import Glyph,icon_sample,scalar
        key='.'.join(path)
        if path[:3]==('apps','fzf','colors'):
            if value is not None:return fzf_sample(self.styles,path[-1],value)
            colors,source=self.fzf()
            if path[-1] in colors:return fzf_sample(self.styles,path[-1],colors[path[-1]],source)
            return Glyph('inherited','0;39','FZF default / caller color' if self.active else 'No active-profile fallback in this scope')
        if self.active and path[:2]==('apps','codex'):
            from codex_toast import color
            from config_codex import GROUPS
            if 'codex' not in self._native:
                from config_codex import Native
                self._native['codex']=Native(self.styles.root,self.styles.selected)
            native=self._native['codex'];source=native.resolve(key)['source']
            field=path[-1];code='0;39'
            if field in ('fg','bg'):
                palette=dict(colors=self.styles.palette,palette=self.styles.native_palette)
                shade=color(value,palette,self.styles.root,'#000000' if field=='bg' else '#ffff00')
                code='0;'+self.styles.sgr_color(shade,field=='bg')
            return Glyph(scalar(value),code,source+(' · termux.'+GROUPS[path[2]].FIELDS[field] if source==str(native.path) else ' (default)'))
        if self.active and path[:2] in (('apps','wttr'),('apps','pkgs')):
            app=path[1]
            if app not in self._native:
                try:
                    from importlib import import_module
                    native=import_module('config_'+app).Native(self.styles.root,self.styles.selected)
                    self._native[app]=str(native.original)
                except (OSError,ValueError,ImportError):self._native[app]=''
            if self._native[app]:
                code='0;39'
                if app=='wttr' and len(path)==4 and path[2] in ('icon_colors','night_icon_colors') and isinstance(value,str):
                    from wttr.styling import Colors
                    colors=Colors();colors.palette=self.styles.palette
                    code='0;'+(colors.sgr(value) or '39')
                return Glyph(scalar(value),code,self._native[app])
        if value is not None:return value
        if path[:3]==('formatting','apps','tmux') and path[-1] in ('main_row','termux_row'):
            from tmux_config import row_positions
            cfg=self.config.get('formatting',{}).get('apps',{}).get('tmux',{})
            _,main,upper=row_positions(cfg,self.styles.selected['facts']['platform'])
            return Glyph(str(main if path[-1]=='main_row' else upper),'0;39','lib/dots/tmux_config.py (automatic row)')
        if key in ('apps.tmux.indicators.working.text','apps.tmux.indicators.waiting.text'):
            state=path[-2];resolved=self.styles.resolve('icons','status.'+state,'tmux')
            sample=icon_sample(self.styles,'apps.tmux.status.'+state,self.styles.icon('status.'+state,app='tmux'))
            source=resolved['declarations'][-1]['key'] if resolved['declarations'] else 'lib/dots/tmux_controls.py'
            return Glyph(sample.text,sample.code,source+' (fallback text)')
        if key=='apps.tmux.indicators.attention.text':
            return Glyph('working/waiting icon','0;39','lib/dots/tmux_controls.py (inherits activity text)')
        if path[:3]==('apps','tmux','battery') and path[-1] in ('critical','low'):
            if not self.active:
                return Glyph('inherited','0;39','Battery provider (not inspected in this scope)')
            config=Path(os.environ.get('BATTERY_CONFIG') or Path(os.environ.get('XDG_CONFIG_HOME') or Path.home()/'.config')/'battery/config')
            tool=Path.home()/'repos/battery/battery'
            variable='BATTERY_'+path[-1].upper()
            if config.exists():return Glyph('inherited','0;39',str(config)+' (battery configuration; not evaluated)')
            value=os.environ.get(variable)
            if value is not None and value.isdigit() and 0<=int(value)<=100:
                return Glyph(value,'0;39',variable+' (environment)')
            match=re.search(r'\$\{'+variable+r':-([0-9]+)\}',read_data(tool))
            if match:return Glyph(match[1],'0;39',str(tool)+' (provider default)')
            return Glyph('inherited','0;39','config/tmux/battery-status.py → battery provider')
        if path[:3] in (('apps','nvim','options'),('apps','nvim','diagnostics')):
            return Glyph('runtime value','0;39','config/nvim/lua/util/dots_config.lua (preserves Neovim '+path[2]+')')
        if path[:4]==('formatting','apps','nvim','lualine'):
            return Glyph('component padding','0;39','config/nvim/lua/util/dots_config.lua (existing Lualine component)')
        if key=='apps.fzf.preview':return Glyph('caller preview','0;39','lib/dots/fzf_config.py (no Config override)')
        return value

    def tree(self,values,path=()):
        # Transform leaves only: the report must never gain additional keys.
        return {key:self.tree(value,(*path,key)) if isinstance(value,dict) else self.leaf((*path,key),value)
                for key,value in values.items()}
