"""Native-adapter environment data; no hooks, shell evaluation or cache writes."""
import json
import os
from pathlib import Path
import sys
import shutil
from environment import declarations, TOKEN, retired_paths, clean_metadata, application_value
from platform_info import detect
from profiles import resolve, SENSITIVE
from profile_environment import Model, RESERVED, IDENTIFIER


def exports(root, env=None, generated=None):
    env = os.environ if env is None else env
    profile = resolve(root, detect(env=env))
    generated = generated or Model(root, profile)
    context = dict(env, DOTS=str(root))
    context.update(generated.scalars)
    context.setdefault('HOME', env.get('USERPROFILE') or str(Path.home()))
    context.setdefault('APPDATA', str(Path(context['HOME']) / 'AppData/Roaming'))
    context.setdefault('LOCALAPPDATA', str(Path(context['HOME']) / 'AppData/Local'))
    data = dict(generated.scalars)
    for key, (template, _) in declarations(root, profile).items():
        if SENSITIVE.search(key) and template and not TOKEN.fullmatch(template):
            raise ValueError('sensitive defaults must reference an environment variable')
        default = (next((name for name in ('nvim','vim','vi','code','nano') if shutil.which(name, path=env.get('PATH',''))), 'vi')
                   if template == '@editor' else TOKEN.sub(lambda match: context.get(match[1], ''), template))
        data[key] = context[key] = application_value(key, context.get(key), default)
    facts = profile['facts']
    data.update(DOTS_PLATFORM=facts['platform'], DOTS_DISTRO=facts['distro'], DOTS_ARCH=facts['architecture'], DOTS_RUNTIME=facts['runtime'],
                DOTS_PROFILE=profile['current'], DOTS_PROFILE_LAYERS=' '.join(row['id'] for row in profile['layers']))
    paths = [str(Path(row['root']) / relative) for row in reversed(profile['layers']) for relative in row.get('path', ['bin','scripts'])
             if (Path(row['root']) / relative).is_dir()]
    previous = env.get('DOTS_PROFILE_PATHS','').split(os.pathsep)
    retired = retired_paths(root, env)
    existing = [entry for entry in env.get('PATH','').split(os.pathsep) if entry not in previous and os.path.normcase(os.path.normpath(entry)) not in retired]
    for key in ('DOTS_ENV_HOOKS','DOTS_ENV_ORIGINS'):
        if key in env: data[key] = clean_metadata(env[key])
    data['DOTS_PROFILE_PATHS'] = os.pathsep.join(paths)
    data['PATH'] = os.pathsep.join(dict.fromkeys([*paths,*existing]))
    data['DOTS_PROFILE_CHECKOUT'] = str(root)
    data['DOTS_PROFILE_BIN_PATHS'] = os.pathsep.join(str(Path(row['root'])/'bin') for row in reversed(profile['layers']))
    data['DOTS_GENERATED_PATHS'] = json.dumps(generated.scalars, ensure_ascii=True)
    return data


def document(root, env=None):
    env = os.environ if env is None else env
    generated = Model(root, resolve(root, detect(env=env)))
    unset = []
    try: previous = json.loads(env.get('DOTS_GENERATED_PATHS', '{}'))
    except (TypeError,ValueError): previous = {}
    oldroot = env.get('DOTS_PROFILE_CHECKOUT')
    if isinstance(previous,dict) and oldroot:
        for name,value in previous.items():
            if (IDENTIFIER.fullmatch(name) and name not in RESERVED and not name.startswith('DOTS_')
                    and name not in generated.scalars and isinstance(value,str)
                    and Path(value).is_relative_to(Path(oldroot)/'profiles') and env.get(name) == value):
                unset.append(name)
    return dict(exports=exports(root,env,generated), maps=generated.maps, unset=unset,
                generated=list(generated.scalars))


if __name__ == '__main__':
    try:
        root=Path(os.environ.get('DOTS') or Path(__file__).resolve().parents[2]).resolve()
        result=document(root)
        data=result['exports']
        if sys.argv[1:] == ['--document']:
            print(json.dumps(result,ensure_ascii=True));sys.exit(0)
        if sys.argv[1:] == ['--fish']:
            # Literal single-quoted strings, never inherited executable code.
            def quote(value): return "'" + value.replace('\\','\\\\').replace("'","\\'") + "'"
            for key,value in data.items():
                values=value.split(os.pathsep) if key=='PATH' else [value]
                print('set -gx '+key+' '+' '.join(map(quote,values)))
        else: print(json.dumps(data,ensure_ascii=True))
    except (OSError,ValueError) as error:
        print('dots environment: '+str(error),file=sys.stderr);sys.exit(1)
