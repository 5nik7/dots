#!/usr/bin/env python3
"""Standalone wttr CLI and private bounded worker entry points."""
import sys
if sys.version_info < (3, 11):
    print('wttr: Python 3.11 or newer is required', file=sys.stderr)
    sys.exit(1)

import argparse
from contextlib import nullcontext
import json
import os
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from core import (ROOT, VERSION, FIELDS, Cache, Unavailable, config, clean, fields,
                  http_fetch, validate_location, validate_language)
from metadata import OPTIONS, COMPLETION_OPTIONS, SHELLS, STOCK_FLAGS, STOCK_DESCRIPTIONS, spellings
sys.path.insert(0, str(ROOT / 'lib/dots'))
from files.catalog import Presentation
from progress import configure, Progress


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError(message)


def parser(options=OPTIONS, prog='wttr'):
    result = Parser(prog=prog, add_help=False, allow_abbrev=False)
    for flag, value, _ in options:
        settings = {}
        if value is None:
            settings['action'] = 'store_true'
        elif '|' in value:
            settings['choices'] = value.split('|')
        result.add_argument(*spellings(flag), **settings)
    result.add_argument('positional', nargs='*')
    return result


def help_view(completion=False):
    from styling import help_banner
    ui = Presentation()
    help_banner(ui)
    ui.emit()
    ui.heading(((ui.icon('weather.title', '') + ' ') if ui.icons else '') + 'wttr — weather from wttr.in')
    ui.detail('Usage', 'wttr completion SHELL [--install] [--dir DIRECTORY]' if completion else 'wttr [LOCATION] [options]')
    if not completion:
        ui.detail('Queries', 'wttr get FIELD | wttr --fields | wttr completion SHELL')
        ui.detail('Browse', 'wttr browse | dots wttr browse; session location/units and cached previews')
        ui.detail('Dots', 'dots wttr accepts the same commands, options and stock requests.')
        ui.detail('Location', 'Explicit input, configured default, then termux-geo city. No IP fallback.')
    ui.emit()
    ui.heading('Options')
    options = [*COMPLETION_OPTIONS, next(row for row in OPTIONS if row[0] == '--help')] if completion else OPTIONS
    for flag, value, description in options:
        ui.detail(', '.join(spellings(flag)) + (' ' + value if value else ''), description)
    ui.emit()
    ui.detail('Examples', "wttr --location London --days 2; wttr --widget; wttr get sunrise")
    if completion:
        ui.detail('Shells', ', '.join(SHELLS))
        ui.detail('Recovery', 'dots files undo TRANSACTION_ID restores a completion install')
    else:
        ui.detail('Stock', 'wttr m2T; wttr m 2 T; wttr format=3; wttr moon@2016-10-25')
        ui.detail('Flags', ' '.join(STOCK_FLAGS) + ' (separate or combined)')
        ui.detail('Pages', 'wttr :help; wttr :bash.function; wttr :translation')
        ui.detail('Formats', 'format=VALUE uses wttr.in; --format TEMPLATE uses local {fields}.')
        ui.detail('Background', 'Widget/daylight use cached city only. --cached never refreshes.')
        ui.detail('Appearance', 'Config controls attribution, temperature ranges, icon colors and widget color format.')
        ui.detail('Styles', 'bold (b), italic (i), underline (u), dim (d), reverse; bright blue selects bright_blue.')
        ui.detail('Widget', '{icon_color}, {temp_color}, {feel_color}, {bold white}, {b}, {reset}; directives select manual styling.')
        ui.detail('Icons', '{location_icon}, {wind_icon}, {sunrise_icon}, {sunset_icon}, {humidity_icon}, {precip_icon}; wind arrows point downwind.')
        ui.detail('Icon styles', '{location_color}, {wind_color}, {sunrise_color}, {sunset_color}, {humidity_color}, {precip_color}.')
        ui.emit()
        ui.heading('Stock wttr.in options')
        for word, description in STOCK_DESCRIPTIONS.items():
            ui.detail(word, description)


def complete(argv):
    from completion import generate, install
    p = Parser(prog='wttr completion', add_help=False, allow_abbrev=False)
    p.add_argument('shell', choices=SHELLS, nargs='?')
    for flag, value, _ in COMPLETION_OPTIONS:
        p.add_argument(flag, **({} if value else {'action': 'store_true'}))
    p.add_argument(*spellings('--help'), action='store_true')
    for key in ('color', 'icons'):
        p.add_argument('--' + key, choices=('auto', 'always', 'never'))
    args = p.parse_args(argv)
    for key in ('color', 'icons'):
        if getattr(args, key): os.environ['DOTS_' + key.upper()] = getattr(args, key)
    if args.help:
        help_view(True)
        return 0
    if bool(args.shell) == args.all or (args.dir and (args.all or not args.install)):
        raise ValueError('choose one shell or --all; --dir requires one shell and --install')
    shells = SHELLS if args.all else (args.shell,)
    if not args.install:
        if args.all:
            raise ValueError('--all requires --install; generate one shell at a time')
        print(generate(args.shell), end='')
        return 0
    configure(human=True)
    ui = Presentation()
    ui.heading('Install wttr completions')
    for shell in shells:
        from completion import FILES
        target = Path(args.dir).absolute() / FILES[shell] if args.dir else ROOT / 'shells' / shell / 'completions' / FILES[shell]
        ui.resource_detail('Target', target, kind='file')
    with Progress('Installing completions'):
        result, targets = install(shells, args.dir)
    ui.detail('Status', result['status'], '92')
    if result.get('id'):
        ui.detail('Transaction', result['id'])
        ui.detail('Undo', 'dots files undo ' + result['id'])
    ui.detail('Activation', 'Load the generated file in your shell; no profile was changed.')
    return 0


def render(row, cfg, args, age, ui=None):
    from styling import condition, temperature_color, Colors, forecast_night, detail_color
    ui = ui or Presentation()
    colors = Colors(enabled=ui.color)
    values = fields(row, cfg, age, icons=ui.icons)
    def temp(value, suffix=''):
        return (value + suffix, colors.sgr(temperature_color(value, cfg)))
    def icon(code, night=False):
        glyph, shade = condition(code, cfg, night)
        glyph = glyph.strip()
        return (glyph + ' ' if ui.icons and glyph else '', colors.sgr(shade) if ui.icons and glyph else None)
    attribution = cfg['show_location_attribution'] and values['attribution']
    label_width = 12 if attribution else 10
    def detail(label, spans):
        ui.detail_spans(label, spans, label_width=label_width, label_gap=cfg['label_gap'])
    def named_icon(name, *, suffix=False):
        glyph = values[name + '_icon']
        text = (' ' + glyph if suffix else glyph + ' ') if glyph else ''
        return (text, colors.sgr(detail_color(name, cfg)) if glyph else None)
    ui.heading_spans([('Weather — ', '1;96'), named_icon('location'), (values['location'], '1;96')])
    detail('Now', [icon(values['code'], values['daylight'] == 'night'),
                   temp(values['temperature'], values['unit'])])
    detail('Condition', [(values['condition'].strip(), None)])
    detail('Feels like', [temp(values['feels_like'], values['unit'])])
    detail('Humidity', [(values['humidity'] + '%', None), named_icon('humidity', suffix=True)])
    detail('Wind', [((values['wind'] + ' ' + values['wind_unit'] + ' ' + values['wind_direction']).rstrip(), None), named_icon('wind', suffix=True)])
    detail('Precip', [(values['precipitation'] + ' ' + values['precipitation_unit'], None), named_icon('precip', suffix=True)])
    detail('Sunrise', [(values['sunrise'] or 'unavailable', None), named_icon('sunrise', suffix=True)])
    detail('Sunset', [(values['sunset'] or 'unavailable', None), named_icon('sunset', suffix=True)])
    if attribution:
        detail('Location data', [(values['attribution'], None)])
    if values['stale'] == 'true':
        detail('Cache', [('Stale (~), ' + values['age'] + ' seconds old', '93')])
    if args.verbose:
        detail('Source', [(row.get('source', 'cache'), None)])
        detail('Age', [(values['age'] + ' seconds', None)])
    if args.current:
        return
    unit = 'F' if cfg['units'] == 'us' else 'C'
    for day in row['data']['weather'][:cfg['days']]:
        ui.emit()
        ui.heading(clean(day.get('date', 'Forecast')))
        detail('Low / High', [temp(clean(day.get('mintemp' + unit, '?'))),
                                      (' / ', None), temp(clean(day.get('maxtemp' + unit, '?')), '°' + unit)])
        hourly = day.get('hourly', [])
        if not isinstance(hourly, list):
            continue
        if not args.hourly:
            midday = next((h for h in hourly if isinstance(h, dict) and str(h.get('time')) == '1200'), {})
            from core import first_value
            detail('Midday', [icon(midday.get('weatherCode'), forecast_night(row['data'], day, 1200)),
                                      ((first_value(midday.get('weatherDesc')) or 'unavailable').strip(), None)])
        else:
            from core import first_value
            for hour in hourly[:8]:
                if not isinstance(hour, dict): continue
                raw_time = str(hour.get('time', ''))
                if not raw_time.isdigit() or not 0 <= int(raw_time) <= 2300: continue
                detail(f'{int(raw_time) // 100:02d}:{int(raw_time) % 100:02d}',
                                [temp(clean(hour.get('temp' + unit, '?')), '°' + unit), (' ', None),
                                 icon(hour.get('weatherCode'), forecast_night(row['data'], day, raw_time)),
                                 (first_value(hour.get('weatherDesc')).strip(), None)])


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ['--_fetch']:
        if len(argv) != 4: return 2
        print(json.dumps(http_fetch(validate_location(argv[1]), validate_language(argv[2]), float(argv[3]))))
        return 0
    if argv[:1] == ['--_worker']:
        try:
            request = json.loads(argv[1])
            _, cfg = config(request['config'])
            cfg.update(language=validate_language(request['language']), timeout=request['timeout'])
            cache = Cache(cfg, request['location'])
            deadline = time.monotonic() + 1
            while True:
                try:
                    cache.refresh(background=True)
                    break
                except OSError:
                    # The scheduling parent may still hold its reservation lock.
                    if time.monotonic() >= deadline: raise
                    time.sleep(.05)
        except (OSError, ValueError, KeyError, IndexError):
            return 1
        return 0
    browser_report = argv[:1] == ['--_browse-report']
    if browser_report:
        argv.pop(0)
    # Consume only leading presentation options; never reinterpret option values.
    while argv and argv[0].split('=')[0] in ('--color', '--icons'):
        flag, separator, value = argv.pop(0).partition('=')
        if not separator:
            if not argv: raise ValueError(flag + ' requires a value')
            value = argv.pop(0)
        if value not in ('auto', 'always', 'never'): raise ValueError('invalid ' + flag)
        os.environ['DOTS_' + flag[2:].upper()] = value
    if argv[:1] == ['browse']:
        from wttr.browser import main as browse
        return browse(argv[1:])
    if 'completion' in argv and argv.index('completion') == 0:
        return complete(argv[1:])
    args = parser().parse_intermixed_args(argv)
    for key in ('color', 'icons'):
        if getattr(args, key): os.environ['DOTS_' + key.upper()] = getattr(args, key)
    if args.help:
        help_view()
        return 0
    if args.version:
        print(VERSION)
        return 0
    if args.positional[:1] == ['completion']:
        return complete(args.positional[1:])
    if args.positional[:1] == ['get']:
        if len(args.positional) != 2 or args.get:
            raise ValueError('usage: wttr get FIELD')
        args.get = args.positional[1]
        args.positional = []
    if args.get and args.get not in FIELDS:
        raise ValueError('unknown field; see --fields')
    from stock import classify
    stock, args.positional = classify(args.positional)
    if stock:
        allowed = {'location', 'config', 'timeout', 'language', 'color', 'icons'}
        for flag, _, _ in OPTIONS:
            key = flag[2:].replace('-', '_')
            if key not in allowed and getattr(args, key) not in (None, False):
                raise ValueError(flag + ' cannot be combined with stock requests')
        if stock['route'] and args.location is not None:
            raise ValueError('moon and service pages do not take --location')
    if args.fields:
        print('\n'.join(FIELDS))
        return 0
    if len(args.positional) > 1 or (args.positional and args.location):
        raise ValueError('supply one location, positionally or with --location')
    explicit = validate_location(args.location if args.location is not None else args.positional[0]) if args.location is not None or args.positional else None
    if args.cached and args.refresh:
        raise ValueError('--cached and --refresh are mutually exclusive')
    if sum(bool(x) for x in (args.json, args.get, args.daylight, args.widget or args.format is not None)) > 1:
        raise ValueError('choose one output mode: JSON, field, daylight or widget')
    path, cfg = config(args.config)
    for key in ('units', 'language'):
        if getattr(args, key): cfg[key] = getattr(args, key)
    validate_language(cfg['language'])
    if args.days: cfg['days'] = int(args.days)
    if args.timeout:
        try: timeout = int(args.timeout)
        except ValueError: raise ValueError('timeout must be an integer from 1 to 60')
        if not 1 <= timeout <= 60: raise ValueError('timeout must be an integer from 1 to 60')
        cfg['timeout'] = timeout
    if stock:
        from stock import fetch as stock_fetch
        configure(human=False)
        output, attribution = stock_fetch(stock, explicit, cfg, args.language)
        sys.stdout.buffer.write(output)
        sys.stdout.buffer.flush()
        if cfg['show_location_attribution'] and attribution and sys.stdout.isatty() and sys.stderr.isatty():
            Presentation(sys.stderr).detail('Location data', attribution)
        return 0
    background = args.widget or args.format is not None or args.daylight
    data_mode = background or args.json or args.get
    configure(human=not data_mode)
    widget_tokens = None
    if args.widget or args.format is not None:
        from styling import parse_widget
        widget_tokens = parse_widget(args.format if args.format is not None else cfg['widget'])
    cache = Cache(cfg, explicit)
    row = cache.read()
    failure = None
    if not args.cached:
        if background and not args.refresh:
            cache.schedule(path)
        elif args.refresh or not cache.usable(row):
            try:
                with Progress('Fetching weather') if not data_mode else nullcontext():
                    row = cache.refresh(background=bool(background), force=args.refresh)
            except (OSError, ValueError) as error:
                failure = error
                row = cache.read()
    if failure is not None and args.refresh and not background and not browser_report:
        raise Unavailable(str(failure))
    usable = cache.usable(row, stale=args.allow_stale or bool(background))
    if args.daylight:
        print(fields(row, cfg, cache.age(row))['daylight'] if usable else 'unknown')
        return 0
    if not usable:
        if background:
            print('?')
            return 0
        raise Unavailable(str(failure) if failure else row.get('error', 'weather unavailable; run wttr --refresh with a location'))
    if args.json:
        print(json.dumps(row['data'], ensure_ascii=False))
    elif args.get:
        print(fields(row, cfg, cache.age(row), icons=os.environ.get('DOTS_ICONS') != 'never')[args.get])
    elif background:
        from styling import widget
        values = fields(row, cfg, cache.age(row), icons=args.icons != 'never' and os.environ.get('DOTS_ICONS') != 'never')
        print(widget(args.format if args.format is not None else cfg['widget'], values, cfg, Presentation(), tokens=widget_tokens))
    else:
        if browser_report and (failure is not None or row.get('error')):
            Presentation(sys.stderr).detail('Refresh', clean(str(failure) if failure is not None else row['error']), '93')
        render(row, cfg, args, cache.age(row))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, OSError) as error:
        ui = Presentation(sys.stderr)
        ui.emit(ui.paint('wttr: ' + str(error), '91'))
        sys.exit(1 if isinstance(error, (Unavailable, OSError)) else 2)
    except KeyboardInterrupt:
        sys.exit(130)
    except BrokenPipeError:
        sys.exit(1)
