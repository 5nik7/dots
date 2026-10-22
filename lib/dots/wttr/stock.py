"""Stock wttr.in syntax and bounded native curl transport; no weather cache."""
from datetime import date
import re
import shutil
import os
import time
from urllib.parse import quote, urlencode

from core import Unavailable, bounded_command, clean, resolve_location
from metadata import STOCK_FLAGS, STOCK_ROUTES


def classify(words):
    """Separate reserved stock tokens from an optional literal location."""
    flags, formats, routes, locations = [], [], [], []
    for word in words:
        if word and all(c in STOCK_FLAGS for c in word):
            flags.append(word)
        elif word.startswith('format='):
            value = word[len('format='):]
            if not value or len(value) > 1024 or clean(value) != value:
                raise ValueError('format= requires a nonempty, control-free template of at most 1024 characters')
            formats.append(value)
        elif word == 'moon' or word.startswith('moon@'):
            if word != 'moon':
                value = word[5:]
                if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
                    raise ValueError('use moon@YYYY-MM-DD with a valid date')
                try:
                    date.fromisoformat(value)
                except ValueError:
                    raise ValueError('use moon@YYYY-MM-DD with a valid date') from None
            routes.append(word)
        elif word in STOCK_ROUTES:
            routes.append(word)
        elif word.startswith(':'):
            raise ValueError('unknown service page; use :help, :bash.function or :translation')
        else:
            locations.append(word)
    if not (flags or formats or routes):
        return None, locations
    if len(formats) > 1 or len(routes) > 1 or (routes and (locations or formats)):
        raise ValueError('choose one stock format or service route; service routes take no location or format')
    return dict(flags=''.join(flags), format=formats[0] if formats else None,
                route=routes[0] if routes else None), locations


def fetch(request, explicit, cfg, language=None):
    curl = shutil.which('curl.exe' if os.name == 'nt' else 'curl')
    if not curl:
        raise Unavailable('stock requests require curl' + ('.exe' if os.name == 'nt' else ''))
    started = time.monotonic()
    attribution = ''
    if request['route']:
        if explicit:
            raise ValueError('moon and service pages do not take --location')
        path = request['route']
    else:
        location, _, attribution = resolve_location(explicit, cfg, False, cfg['timeout'])
        path = quote(location, safe='')
    query = [request['flags']] if request['flags'] else []
    if request['format'] is not None:
        query.append(urlencode({'format': request['format']}))
    if language:
        query.append(urlencode({'lang': language}))
    url = 'https://wttr.in/' + path + ('?' + '&'.join(query) if query else '')
    remaining = cfg['timeout'] - (time.monotonic() - started)
    if remaining <= 0:
        raise Unavailable('location timed out')
    # -q must be first: user curlrc files must not add output files or requests.
    # No shell, redirects, retries or curl glob expansion; the origin is fixed.
    command = [curl, '-q', '--silent', '--fail', '--globoff', '--proto', '=https',
               '--max-time', str(remaining), '--url', url]
    try:
        return bounded_command(command, remaining), attribution
    except (OSError, Unavailable) as error:
        raise Unavailable('stock wttr.in request failed: ' +
                          (str(error) if isinstance(error, Unavailable) else 'curl unavailable')) from error
