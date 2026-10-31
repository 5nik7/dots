"""Literal FZF preferences with a constrained projection for owned pickers."""
import re
import shlex

ATTRS=set('regular bold dim italic underline blink reverse strikethrough strip nobold nodim noitalic nounderline noblink noreverse nostrikethrough'.split())
# Pickers own the records, identity/matching columns, previews, events and actions.
# Only presentation/matching preferences that cannot change those protocols pass.
SAFE_OPTIONS=set('style layout border info pointer marker gutter gutter-raw separator scrollbar no-separator no-scrollbar no-border no-info no-bold unicode no-unicode cycle no-cycle smart-case ignore-case case-sensitive exact no-exact track no-track scroll-off tabstop ellipsis hscroll-off'.split())
SAFE_ACTIONS=set('up down up-match down-match page-up page-down half-page-up half-page-down first last toggle-preview preview-up preview-down preview-page-up preview-page-down toggle-wrap toggle-raw'.split())
PROTECTED_KEYS=set('enter esc ctrl-c tab btab ctrl-a ctrl-d alt-p alt-j alt-k alt-c f1'.split())


def validate_color(value):
    from style_config import validate
    if not isinstance(value,str):raise ValueError('FZF colors require a native color/style string')
    for token in value.split(':'):
        if token in ATTRS or token=='-1' or token.isdigit() and 0<=int(token)<=255:continue
        validate('colors',{'ui.foreground.fg':token})


def colors(options,styles):
    result=[]
    for key,value in options.get('colors',{}).items():
        if value is None:continue
        validate_color(value)
        atoms=[]
        for token in value.split(':'):
            resolved=styles.color(token) if styles else token
            if token in ('default','reset'):resolved='-1'
            elif token not in ATTRS and not token.isdigit() and token!='-1' and not resolved.startswith('#'):
                from style_config import ANSI,ALIASES
                number=ANSI.get(ALIASES.get(token,token),39)
                resolved=str(number-30 if 30<=number<=37 else number-90+8 if 90<=number<=97 else -1)
            atoms.append(resolved)
        result.append(key+':'+':'.join(atoms))
    return ','.join(result)


def shell_options(options):
    flags=list(options.get('default_opts',[]))
    if options.get('bindings'):flags.append('--bind='+','.join(key+':'+value for key,value in options['bindings'].items()))
    if options.get('preview_window') is not None:flags.append('--preview-window='+options['preview_window'])
    if options.get('preview') is not None:flags.append('--preview='+options['preview'])
    return shlex.join(flags)


def picker_options(options):
    flags=[];ignored=[]
    for option in options.get('default_opts',[]):
        key=option.split('=',1)[0].removeprefix('--')
        if key in ('border','no-border'):ignored.append(option.split('=',1)[0]+' (apps.menu.popup.border)')
        elif key in SAFE_OPTIONS and option.startswith('--'):flags.append(option)
        elif option in ('-x','-e','+x','+e','-i','+i'):flags.append(option)
        else:ignored.append(option.split('=',1)[0])
    for key,action in options.get('bindings',{}).items():
        if re.fullmatch(r'[a-z0-9-]+',key) and key not in PROTECTED_KEYS and action in SAFE_ACTIONS:
            flags.append('--bind='+key+':'+action)
        else:ignored.append('binding:'+key)
    if options.get('preview') is not None:ignored.append('preview (owned preview)')
    if options.get('preview_window') is not None:ignored.append('preview_window (owned layout)')
    return flags,ignored
