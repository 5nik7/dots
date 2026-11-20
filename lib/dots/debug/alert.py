"""Explicit local device test; no Codex event, installation or queue access."""
import importlib.util
import os

MESSAGE = 'Dots Codex alert test: toast and vibration'


def run(root, alert_type='regular'):
    from config_codex import Native
    native=Native(root)
    result=dict(version=1,message=MESSAGE,source=str(native.path),alert_type=alert_type,settings=native.values['alerts'][alert_type])
    if os.name=='nt' or not os.environ.get('TERMUX_VERSION'):
        result.update(results={name:dict(status='unavailable',reason='Termux is required') for name in ('toast','vibrate')},exit_code=1)
        return result
    spec=importlib.util.spec_from_file_location('dots_debug_codex_alert',root/'config/tmux/codex-alerts.py')
    bridge=importlib.util.module_from_spec(spec);spec.loader.exec_module(bridge)
    prefs=bridge.preferences(native.declared)
    result['results']=bridge.notify_device(MESSAGE,prefs,wait=True,kind=alert_type)
    result['exit_code']=int(any(row['status'] in ('failed','unavailable','cancelled') for row in result['results'].values()))
    return result
