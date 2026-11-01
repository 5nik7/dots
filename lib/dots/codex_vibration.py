"""Codex vibration schema and finite, sequential Termux API requests."""
import subprocess
import time

FIELDS = dict(duration='vibration_ms', force='force_vibration', count='vibration_count')
DEFAULTS = dict(duration=300, force=True, count=1)
KEYS = tuple('apps.codex.vibrate.'+key for key in FIELDS)
GAP_SECONDS = 0.15


def validate(field, value):
    if field=='force':
        if type(value) is not bool: raise ValueError('vibration force requires true or false')
    elif field in ('duration','count'):
        low,high=(1,10000) if field=='duration' else (0,10)
        if type(value) is not int or not low<=value<=high:
            raise ValueError('vibration '+field+' requires an integer '+str(low)+'..'+str(high))
    else: raise ValueError('unknown Codex vibration field')


def values(options):
    result={key:options.get(native,DEFAULTS[key]) for key,native in FIELDS.items()}
    for key,value in result.items(): validate(key,value)
    return result


def constraints(key):
    field=key.removeprefix('apps.codex.vibrate.')
    if field not in FIELDS: return {}
    result=dict(default=DEFAULTS[field])
    if field=='force': result.update(type='boolean',choices=[True,False])
    elif field=='count': result.update(type='integer',choices=list(range(11)),syntax='0 disables vibration; 1..10 pulses per alert')
    else: result.update(type='integer',examples=[100,300,500,1000],syntax='Integer 1..10000 milliseconds per pulse')
    return result


def run(settings, request, *, sleep=time.sleep, cancel=None):
    """Wait for each accepted pulse to finish before asking for the next."""
    if set(settings)!=set(FIELDS): raise ValueError('invalid vibration settings')
    for key,value in settings.items(): validate(key,value)
    result=dict(status='skipped' if not settings['count'] else 'sent',requested=settings['count'],attempted=0,sent=0)
    if not settings['count']: result['reason']='Vibration count is zero'
    command=['termux-vibrate','-d',str(settings['duration'])]+(['-f'] if settings['force'] else [])
    for index in range(settings['count']):
        if cancel is not None and cancel.is_set():
            result.update(status='cancelled',reason='Vibration sequence cancelled');break
        result['attempted']+=1
        try: request(command,timeout=5)
        except (OSError,ValueError,subprocess.SubprocessError):
            result.update(status='failed',reason='Vibration request failed or timed out');break
        result['sent']+=1
        if index+1<settings['count']:
            delay=settings['duration']/1000+GAP_SECONDS
            if cancel is None: sleep(delay)
            else: cancel.wait(delay)
    return result
