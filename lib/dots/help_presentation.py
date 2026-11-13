"""Inert help syntax and preference resolution, shared by public help adapters.

This module is cheap to import from the literal shell-settings projection.  The
ordinary Presentation class is loaded only when a help view is requested.
"""
import os
import re
import sys

TAGLINE = 'Manage your dotfiles and more...'
HUES = dict(executable='cyan', command='blue', subcommand='magenta',
            option='yellow', argument='green')
ROLES = (*HUES, 'heading', 'description', 'punctuation', 'tagline')
FALLBACK = dict(executable='36', command='34', subcommand='35', option='33',
                argument='32', heading='1;96', description='39',
                punctuation='90', tagline='39')


class HelpStyles:
    def __init__(self, root=None, selected=None, palette=None, styles=None, controls=None):
        from style_config import Styles, current as current_styles
        from config_values import Controls, current as current_controls
        active = root is None and selected is None and styles is None
        self.styles = styles if styles is not None else (current_styles() if active and palette is None else None)
        if self.styles is None:
            self.styles = Styles(root, selected, palette=palette)
        self.controls = controls
        if self.controls is None and active:
            try:
                self.controls = current_controls()
            except (OSError, ValueError):
                # Bootstrap/legacy checkouts can have no profile definitions
                # even when their launcher exports a platform identity. Reuse
                # the resolved style context; malformed actual inputs still
                # fail validation in Controls below.
                pass
        if self.controls is None:
            self.controls = Controls(self.styles.root, self.styles.selected)
        self.tagline = self.controls.values.get('apps', {}).get('cli', {}).get('tagline', TAGLINE)
        if not isinstance(self.tagline, str) or any(not c.isprintable() for c in self.tagline):
            self.tagline = TAGLINE
        self._codes = {}
        self.tagline_fallback = False

    def code(self, role):
        if role not in ROLES:
            role = 'description'
        if role not in self._codes:
            self._codes[role] = '0;' + self.styles.sgr_fields(self.style(role))
        return self._codes[role]

    def style(self, role):
        styles = self.styles
        base = ('ui.heading' if role == 'heading' else 'ui.muted' if role == 'punctuation'
                else 'ui.foreground')
        generic = {'fg': 'bright_cyan', 'bold': True} if role == 'heading' else {'fg': 'muted' if role == 'punctuation' else 'foreground'}
        fallback = dict(fg=HUES[role]) if role in HUES else styles.style(base, fallback=generic, app='cli')
        if role == 'heading':
            fallback.setdefault('bold', True)
        if role == 'tagline':
            fallback['fg'] = 'accent' if styles.palette.get('accent') else fallback.get('fg', 'foreground')
        fields = styles.style('help.' + role, fallback=fallback, app='cli')
        # Global accent's normal ANSI-blue fallback is deliberately not used
        # for the tagline. Explicit non-accent user colors still win.
        if role == 'tagline':
            token=fields.get('fg');seen=set()
            while isinstance(token,str) and token.startswith('colors.') and token not in seen:
                seen.add(token);token=styles.resolve('colors',token[7:])['value']
            self.tagline_fallback = token == 'accent' and not styles.palette.get('accent')
            if self.tagline_fallback:
                fields['fg'] = styles.style('ui.foreground', app='cli').get('fg', 'foreground')
        return fields

    def rows(self):
        for role in ROLES:
            yield '__help.color.' + role, self.code(role), 'style'
        yield '__help.tagline', self.tagline, 'literal'


# Quoting is recognized only to retain literal argument boundaries. Nothing is
# expanded, parsed as executable shell, or passed to a command interpreter.
TOKEN = re.compile(r'''(?:"(?:\\.|[^"\\])*"|'[^']*'|\\.|[^\s\[\]{}(),|=;<>]+)|\s+|.''')
PLACEHOLDERS = {'OPTIONS': 'option', 'OPTION': 'option', 'FLAGS': 'option',
                'COMMAND': 'command', 'COMMANDS': 'command', 'SUBCOMMAND': 'subcommand'}


def _commands(commands):
    result = set()
    for item in commands:
        if isinstance(item, (tuple, list)):
            result.update(item)
        else:
            result.update(str(item).split())
    return result


def syntax_spans(text, *, prog='dots', route=(), kind='syntax', commands=(), options=None):
    """Return exact text plus role names; never insert ANSI before layout."""
    text = str(text)
    if kind == 'description':
        return description_spans(text, prog=prog, route=route, commands=commands)
    if kind in ('heading', 'punctuation', 'tagline'):
        return [(text, kind)]
    if kind == 'example':
        kind, route = 'syntax', ()
    program = str(prog or 'dots').split()
    executable = program[0] if program else 'dots'
    route = tuple(route.split() if isinstance(route, str) else route) or tuple(program[1:])
    command_routes = [tuple(item) if isinstance(item, (tuple, list)) else tuple(str(item).split()) for item in commands]
    prefix=tuple(program[1:])
    if prefix:
        command_routes=[item if item[:len(prefix)]==prefix else (*prefix,*item) for item in command_routes]
    original_routes = command_routes
    seen_route = []
    options = options or {}
    expected = list(route)
    spans, depth = [], 0
    active_route = kind in ('syntax', 'command', 'subcommand')
    if kind in ('command', 'subcommand') and expected and text.lstrip().split(' ',1)[0] not in (executable, expected[0]):
        # A parser's command rows omit its existing invocation prefix.
        seen_route = list(expected); depth = len(expected); expected = []
    first = True
    brackets = 0
    groups = []
    after_options = False
    value = False
    restart = False
    for match in TOKEN.finditer(text):
        word = match[0]
        if word.isspace():
            role = 'description'
        elif word in ('[', ']', '{', '}', '(', ')', ',', '|', '=', ';', '<', '>') or word == '...':
            role = 'punctuation'
            if word in ('[', '{', '('):
                groups.append((list(seen_route),depth,value,active_route,list(expected)))
            elif word in (']', '}', ')') and groups:
                seen_route,depth,value,active_route,expected = groups.pop()
                seen_route=list(seen_route); expected=list(expected)
                value = False
            elif word in (',', '|'):
                if groups:
                    seen_route,depth,value,active_route,expected = groups[-1]
                    seen_route=list(seen_route);expected=list(expected)
                elif spans and any(r in ('command','subcommand') for _,r in spans[-2:]) and seen_route:
                    seen_route=seen_route[:-1];depth=max(0,depth-1)
            if word == '[': brackets += 1
            elif word == ']': brackets = max(0, brackets-1)
            if word == '=':
                value = True
            if word == ';':
                value = False; first = True; seen_route = []; depth = 0
                expected = list(route); active_route = True; after_options = False
            if word == '|':
                restart = True
        elif (first or restart) and kind not in ('argument', 'option') and (word == 'dots' or word == executable or word.rsplit('/', 1)[-1] == executable):
            role = 'executable'
            first = False; seen_route = []; depth = 0; active_route = True
            after_options = False; value = False
            if word == 'dots' and executable != 'dots':
                expected = [executable, *route]
                command_routes = [(executable, *item) for item in original_routes]
            else:
                expected = list(route); command_routes = original_routes
        elif word == '--':
            role = 'option'; after_options = True; active_route = False; first = False
        elif not after_options and re.fullmatch(r'--?[A-Za-z0-9][A-Za-z0-9_-]*', word):
            role = 'option'; value = options.get(word, word not in ('--help', '-h')); first = False
        elif not after_options and word.rstrip('.') in PLACEHOLDERS and not value:
            role = PLACEHOLDERS[word.rstrip('.')]; first = False
        elif brackets and not after_options and word.rstrip('.').lower() in ('options', 'option', 'flags', 'args', 'arguments'):
            role = 'option' if word.rstrip('.').lower() in ('options', 'option', 'flags') else 'argument'
            first = False
        elif active_route and not value and (expected and word == expected[0]):
            role = 'command' if depth == 0 and kind != 'subcommand' else 'subcommand'
            expected.pop(0); seen_route.append(word); depth += 1; first = False
        elif active_route and not value and (any(candidate[:len(seen_route)+1] == (*seen_route, word) for candidate in command_routes) or
                                             (not commands and kind in ('command', 'subcommand') and re.fullmatch(r'[a-z][a-z0-9_-]*', word))):
            role = 'command' if depth == 0 and kind != 'subcommand' else 'subcommand'
            seen_route.append(word); depth += 1; first = False
        else:
            role = 'argument'
            if not value:
                active_route = False
            value = False; first = False
        if not word.isspace() and word != '|':
            restart = False
        # Ellipses belong to grammar punctuation even when attached to ARGS.
        if role != 'punctuation' and word.endswith('...') and len(word) > 3:
            spans.extend(((word[:-3], role), ('...', 'punctuation')))
        else:
            spans.append((word, role))
    return spans


def description_spans(text, *, prog='dots', route=(), commands=()):
    """Style explicitly delimited snippets/flags and known invocation spans."""
    route = tuple(route.split() if isinstance(route, str) else route)
    executable = str(prog or 'dots').split()[0]
    references = [*commands, 'help', 'commands']
    if executable != 'dots':
        references.append(executable)
        references.extend((executable, *(item if isinstance(item,(tuple,list)) else str(item).split())) for item in commands)
    known = _commands(references) | set(route)
    # Backticks are authored syntax markers. A bare invocation is bounded by
    # its known route, uppercase placeholders and options; normal prose stops it.
    executables = {executable, 'dots'}
    pattern = re.compile(r'`[^`\n]+`|(?<![\w-])--?[A-Za-z][\w-]*(?:=[^\s,;]+)?|(?<![\w/-])(?:' + '|'.join(re.escape(x) for x in sorted(executables)) + r')(?=\s|$)')
    result, offset = [], 0
    for match in pattern.finditer(text):
        if match.start() < offset:
            continue
        if match.start() > offset:
            result.append((text[offset:match.start()], 'description'))
        token = match[0]
        end = match.end()
        if token.startswith('`'):
            result.append(('`', 'punctuation'))
            result.extend(syntax_spans(token[1:-1], prog=prog, commands=references))
            result.append(('`', 'punctuation'))
        elif token in executables:
            for following in re.finditer(r'\s+(\S+)', text[end:]):
                candidate = following[1].rstrip('.,;:')
                if candidate in known or re.fullmatch(r'\[?[A-Z][A-Z0-9_.]*\]?', candidate) or candidate.startswith('--'):
                    end = match.end() + following.end(1) - (len(following[1]) - len(candidate))
                else:
                    break
            result.extend(syntax_spans(text[match.start():end], prog=token, commands=references))
        else:
            result.extend(syntax_spans(token, prog=prog, kind='option', commands=known))
        offset = end
    if offset < len(text):
        result.append((text[offset:], 'description'))
    return result


def _enabled(stream=None, color=None):
    if color is not None:
        return bool(color)
    stream = stream if stream is not None else sys.stdout
    mode = os.environ.get('DOTS_COLOR', 'auto')
    return mode == 'always' or (mode == 'auto' and stream.isatty() and
                               os.environ.get('TERM', 'dumb') != 'dumb' and not os.environ.get('NO_COLOR'))


def _parser_commands(parser, prefix=()):
    result = []
    if parser is not None:
        for action in getattr(parser, '_actions', ()):
            choices = getattr(action, 'choices', None)
            if isinstance(choices, dict) and all(hasattr(child, '_actions') for child in choices.values()):
                for name, child in choices.items():
                    result.append((*prefix, name))
                    result.extend(_parser_commands(child, (*prefix, name)))
    return result


def _parser_options(parser):
    result = {}
    if parser is not None:
        for action in getattr(parser, '_actions', ()):
            for flag in getattr(action, 'option_strings', ()):
                result[flag] = action.nargs != 0
            choices = getattr(action, 'choices', None)
            if isinstance(choices, dict):
                for child in choices.values():
                    if hasattr(child, '_actions'):
                        result.update(_parser_options(child))
    return result


def colorize_help(text, *, prog='', parser=None, commands=(), color=None, stream=None, palette=None):
    """Decorate already laid-out parser help without changing plain bytes.

    Parsers perform their own layout on inert text. This adapter attaches roles
    afterward; custom help views use HelpPresentation to wrap semantic spans.
    """
    if not _enabled(stream, color):
        return text
    styles = HelpStyles(palette=palette)
    prog = prog or getattr(parser, 'prog', '') or 'dots'
    command_routes = [*commands, *_parser_commands(parser, tuple(prog.split()[1:]))]
    known = _commands(command_routes)
    direct_commands = set()
    for action in getattr(parser,'_actions',()):
        choices = getattr(action,'choices',None)
        if isinstance(choices,dict) and all(hasattr(child,'_actions') for child in choices.values()):
            direct_commands.update(choices)
    options = _parser_options(parser)
    program = prog.split()[0]
    section, usage = '', False
    output = []
    lines=text.splitlines(keepends=True)
    skip_until=0
    for line_number,line in enumerate(lines):
        if line_number<skip_until:continue
        ending = '\n' if line.endswith('\n') else ''
        body = line[:-1] if ending else line
        if '\033' in body:  # Authored artwork / existing exact swatches.
            output.append(line); continue
        stripped = body.strip()
        if not stripped:
            output.append(line); usage = False; continue
        spans = []
        match = re.match(r'(\s*(?:usage|Usage)\s*:?\s+)(.*)', body)
        if match:
            content=match[2]+ending
            skip_until=line_number+1
            while skip_until<len(lines) and lines[skip_until].strip() and lines[skip_until][0].isspace():
                content+=lines[skip_until];skip_until+=1
            spans = [(match[1], 'heading'), *syntax_spans(content, prog=prog, commands=command_routes, options=options)]
            ending='';usage=False
        elif stripped.lower().rstrip(':') in ('usage', 'options', 'global options', 'commands', 'subcommands', 'actions', 'arguments', 'positional arguments', 'examples', 'notes', 'optional arguments') or (not body.startswith(' ') and stripped.endswith(':')):
            section = stripped.lower().rstrip(':'); usage = section == 'usage'
            spans = [(body, 'heading')]
        elif stripped.startswith((program + ' ', '$ ' + program + ' ')) or stripped == program:
            prefix = body[:len(body)-len(body.lstrip())]
            if stripped.startswith('$ '):
                prefix += '$ '; stripped = stripped[2:]
            spans = [(prefix, 'punctuation'), *syntax_spans(stripped, prog=prog, commands=command_routes, options=options)]
        elif usage and body.startswith(' '):
            spans = syntax_spans(body, prog=prog, kind='argument', commands=command_routes)
        else:
            row = re.match(r'(\s*)(\S.*?)(\s{2,})(\S.*)', body)
            if row and (row[2].startswith('-') or section in ('commands', 'subcommands', 'actions', 'arguments', 'positional arguments', 'options', 'optional arguments')):
                label_words=set(re.findall(r'[A-Za-z0-9_-]+',row[2]))
                command_label=bool(label_words) and label_words<=direct_commands
                kind = 'option' if row[2].startswith('-') else 'command' if command_label or section in ('commands', 'subcommands', 'actions') else 'argument'
                spans = [(row[1], 'description'), *syntax_spans(row[2], prog=prog, kind=kind, commands=command_routes),
                         (row[3], 'description'), *description_spans(row[4], prog=prog, commands=command_routes)]
            elif (set(re.findall(r'[A-Za-z0-9_-]+',stripped))<=direct_commands and direct_commands) or (stripped.split()[0] in known and section in ('commands', 'subcommands', 'actions')):
                spans = syntax_spans(body, prog=prog, commands=command_routes, kind='command')
            elif stripped.startswith('-') and section in ('options', 'optional arguments', 'global options'):
                spans = syntax_spans(body, prog=prog, kind='option')
            else:
                spans = description_spans(body, prog=prog, commands=command_routes)
        output.append(''.join('\033[' + styles.code(role) + 'm' + value + '\033[0m' if value and not value.isspace() else value
                              for value, role in spans) + ending)
    return ''.join(output)


def __getattr__(name):
    if name != 'HelpPresentation':
        raise AttributeError(name)
    from files.catalog import Presentation
    from resources import cells, wrap
    from row_layout import width as layout_width, pad

    class HelpPresentation(Presentation):
        def __init__(self, stream=None, *, root=None, palette=None, **kwargs):
            super().__init__(stream, **kwargs)
            self.help_styles = HelpStyles(root=root, palette=palette)

        def _help_spans(self, text, **kwargs):
            return [(value, self.help_styles.code(role)) for value, role in syntax_spans(text, **kwargs)]

        def heading(self, title):
            self._spans([(title, self.help_styles.code('heading'))])

        def help_text(self, text, *, kind='description', prog='dots', route=(), commands=(), indent=0):
            self._spans(self._help_spans(text, kind=kind, prog=prog, route=route, commands=commands), ' '*indent)

        def help_row(self, label, description, *, kind='syntax', value_kind='description', prog='dots', route=(), commands=(), label_width=None, indent=None, label_gap=None):
            label = self.clean(label)
            indent = self.detail_indent if indent is None else indent
            gap = self.formatting.get('label_gap', 1) if label_gap is None else label_gap
            indent = min(indent, max(0, self.width-8))
            gap = min(gap, max(0, self.width-indent-8))
            requested = self.formatting.get('label_width', 10) if label_width is None else label_width
            width = layout_width(requested, self.width, indent=indent, gap=gap)
            left = self._help_spans(label, kind=kind, prog=prog, route=route, commands=commands)
            right = self._help_spans(description, kind=value_kind, prog=prog, route=route, commands=commands)
            if (width and cells(label) > width) or cells(label)+indent+gap > self.width-8:
                self._spans(left, ' '*indent)
                if description:
                    self._spans(right, ' '*(indent+width+gap))
            else:
                padded = pad(label, width, self.formatting.get('alignment', 'left'))
                before = len(padded)-len(padded.lstrip())
                after = len(padded)-len(label)-before
                prefix = ' '*(indent+before)+''.join(self.paint(text, code) for text,code in left)+' '*(after+gap)
                continuation = ' '*(indent+cells(padded)+gap)
                right = [(self.clean(text), code) for text,code in right if text]
                if not right:
                    self.emit(prefix); return
                index, offset = 0, 0
                for number, part in enumerate(wrap(''.join(text for text,_ in right), max(1,self.width-len(continuation)))):
                    line = prefix if number == 0 else continuation
                    remaining = len(part)
                    while remaining:
                        text,code = right[index]
                        count = min(remaining,len(text)-offset)
                        line += self.paint(text[offset:offset+count],code)
                        remaining -= count; offset += count
                        if offset == len(text):index += 1;offset = 0
                    self.emit(line)

    globals()['HelpPresentation'] = HelpPresentation
    return HelpPresentation
