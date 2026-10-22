"""One static option vocabulary for help, parser and completion. No providers."""
OPTIONS = [
    ('--location', 'LOCATION', 'Override configured location or automatic city'),
    ('--current', None, 'Show current conditions only'),
    ('--days', '1|2|3', 'Number of forecast days (default: 3)'),
    ('--hourly', None, 'Include three-hourly forecast rows'),
    ('--units', 'us|metric', 'Temperature, wind and precipitation units'),
    ('--language', 'CODE', 'Weather description language (default: en)'),
    ('--widget', None, 'Print a compact cached widget; refresh in background'),
    ('--format', 'TEMPLATE', 'Widget template with literal {field} placeholders'),
    ('--get', 'FIELD', 'Print one field; also: wttr get FIELD'),
    ('--fields', None, 'List available template and scalar fields'),
    ('--json', None, 'Print the original wttr.in j1 object'),
    ('--daylight', None, 'Print day, night or unknown; refresh in background'),
    ('--refresh', None, 'Refresh now, overriding freshness and cooldown'),
    ('--cached', None, 'Read only; never spawn, locate, lock or write'),
    ('--allow-stale', None, 'Allow marked weather up to max_stale age'),
    ('--config', 'PATH', 'Use this TOML configuration file'),
    ('--timeout', 'SECONDS', 'Total refresh deadline (1–60 seconds)'),
    ('--color', 'auto|always|never', 'Human and widget output colors'),
    ('--icons', 'auto|always|never', 'Weather icons (widget auto uses icons)'),
    ('--verbose', None, 'Show cache provenance and age in human output'),
    ('--help', None, 'Show usage without querying providers'),
    ('--version', None, 'Print version'),
]
SHELLS = ('bash', 'zsh', 'fish', 'powershell')
STOCK_FLAG_DESCRIPTIONS = {
    'm': 'Metric (SI) units',
    'u': 'US customary units',
    'M': 'Wind speed in meters per second',
    '0': 'Current weather only',
    '1': 'Current weather and today forecast',
    '2': 'Current weather, today and tomorrow forecasts',
    'A': 'Ignore User-Agent and force ANSI terminal output',
    'd': 'Restrict output to standard console font glyphs',
    'F': 'Hide the Follow line',
    'n': 'Narrow view with only day and night',
    'q': 'Quiet: hide the Weather report heading',
    'Q': 'Superquiet: hide heading and city name',
    'T': 'Disable terminal sequences and colors',
}
STOCK_FLAGS = ''.join(STOCK_FLAG_DESCRIPTIONS)
STOCK_ROUTES = (':help', ':bash.function', ':translation')
STOCK_DESCRIPTIONS = {**STOCK_FLAG_DESCRIPTIONS,
    'format=': 'Upstream format preset or percent template',
    'moon': 'Current Moon phase',
    'moon@': 'Moon phase for YYYY-MM-DD',
    ':help': 'Show upstream usage',
    ':bash.function': 'Show the recommended Bash function',
    ':translation': 'Show translation and contributor information',
}
STOCK_WORDS = tuple(STOCK_DESCRIPTIONS)
COMPLETION_OPTIONS = [('--all', None, 'Generate/install all shells'),
                      ('--install', None, 'Install with backup and a Dots transaction'),
                      ('--dir', 'DIRECTORY', 'Override destination directory for one shell')]
