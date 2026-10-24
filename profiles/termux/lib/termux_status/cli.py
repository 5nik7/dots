"""Shared public CLI for Android status commands."""

import argparse
import json
import re
import string
import sys

from . import cache
from .display import COMMON_FIELDS, DATA_FIELDS, snapshot
from .providers import STREAMS


ALIASES = {"get": "--get", "format": "--format", "completion": "--completion"}
SHELLS = ("bash", "zsh", "fish")
OPTIONS = (
    (("--icon",), "print a Nerd Font icon (default)", None, "mode"),
    (("--text",), "print an ASCII status label", None, "mode"),
    (("--both",), "print icon and text", None, "mode"),
    (("--json",), "print the normalized snapshot", None, "mode"),
    (("-g", "--get"), "print one field", "field", "mode"),
    (("-f", "--format"), "render {field} placeholders", "template", "mode"),
    (("--fields",), "list available fields without polling", None, "mode"),
    (("--completion",), "print shell completion source", "shell", "mode"),
    (("--cached",), "read cache without refreshing", None, "selector"),
    (("--refresh",), "refresh now; enable successful providers", None, "selector"),
    (("--no-newline",), "omit the final newline", None, "selector"),
    (("--install",), "install completion files", None, "install"),
    (("--all",), "install completions for all three shells", None, "install"),
    (("--dir",), "install into this exact directory", "directory", "install"),
    (("-h", "--help"), "show help and exit", None, "help"),
)
EXTRA_OPTIONS = {
    "volume": ((("--stream",), "audio stream (default: music)", "stream", "selector"),),
    "cell": ((("--cell",), "select a 1-based registered-cell index", "cell", "selector"),),
    "notification": (
        (("--include-self",), "include Termux notifications", None, "selector"),
        (("--include-package",), "include only this package (repeatable)", "package", "selector"),
        (("--exclude-package",), "exclude this package (repeatable)", "package", "selector"),
    ),
}


def normalize_args(argv, options):
    value_flags = {name for names, _, kind, _ in options if kind for name in names}
    result, awaiting = [], False
    for arg in argv:
        if awaiting:
            result.append(arg)
            awaiting = False
            if not arg.startswith("-"):
                continue
        else:
            arg = ALIASES.get(arg, arg)
            result.append(arg)
        awaiting = arg in value_flags
    return result


def template_fields(template, fields):
    requested = set()
    for _, name, spec, conversion in string.Formatter().parse(template):
        if name is None:
            continue
        if name not in fields or spec or conversion:
            raise ValueError("use plain {field} placeholders from --fields; escape braces as {{ and }}")
        requested.add(name)
    return requested


def scalar(value):
    if type(value) is bool:
        return "true" if value else "false"
    return str(value)


def main(module, argv=None):
    options = OPTIONS + EXTRA_OPTIONS.get(module, ())
    fields = COMMON_FIELDS + DATA_FIELDS[module]
    command = "termux-" + module + "-status"
    parser = argparse.ArgumentParser(
        prog=command, add_help=False,
        description=f"Cached Android {module} indicator for tmux, Starship and shells.",
        epilog="Aliases: get FIELD, format TEMPLATE, completion SHELL. Default reads return immediately "
               "and request a one-shot refresh when needed. Cellular/notifications require --refresh first. "
               "Failed providers require another --refresh. ~ marks stale data (at most five minutes old). "
               "Use --cached to prevent all refresh work. Location reads the toggle, never coordinates.")
    modes = parser.add_mutually_exclusive_group()
    freshness = parser.add_mutually_exclusive_group()
    for names, description, kind, group in options:
        kwargs = {"help": description}
        target = modes if group == "mode" else freshness if names[0] in ("--cached", "--refresh") else parser
        if group == "help":
            kwargs["action"] = "help"
        elif kind is None:
            kwargs["action"] = "store_true"
        elif kind == "field":
            kwargs["choices"] = fields
        elif kind == "shell":
            kwargs.update(nargs="?", const="", choices=("", *SHELLS))
        elif kind == "cell":
            kwargs["type"] = int
        elif kind == "stream":
            kwargs.update(choices=STREAMS, default="music")
        elif kind == "package":
            kwargs.update(action="append", default=[])
        target.add_argument(*names, **kwargs)
    args = parser.parse_args(normalize_args(sys.argv[1:] if argv is None else argv, options))
    if getattr(args, "cell", None) is not None and args.cell < 1:
        parser.error("--cell must be positive")
    for package in getattr(args, "include_package", []) + getattr(args, "exclude_package", []):
        if not re.fullmatch(r"[A-Za-z0-9_.]+", package):
            parser.error("package names may contain letters, numbers, underscores and dots")
    if args.completion is not None:
        if args.all and (not args.install or args.completion):
            parser.error("--all requires --install and no individual shell")
        if not args.all and not args.completion:
            parser.error("completion requires bash, zsh, fish, or --all --install")
        if args.dir is not None and (not args.install or not args.dir):
            parser.error("--dir requires --install and a nonempty directory")
        from .completions import completion_source, completion_targets, install_completions
        if args.install:
            try:
                targets = completion_targets(command, SHELLS if args.all else (args.completion,), args.dir)
                install_completions(command, fields, options, targets)
            except OSError as error:
                print(f"{command}: {error}; completed installs/backups are listed above", file=sys.stderr)
                return 1
        else:
            print(completion_source(command, fields, options, args.completion), end="")
        return 0
    if args.install or args.all or args.dir is not None:
        parser.error("--install, --all and --dir require completion")
    if args.fields:
        print("\n".join(fields))
        return 0
    try:
        requested = {args.get} if args.get is not None else template_fields(args.format, fields) if args.format is not None else set()
    except ValueError as error:
        parser.error(str(error))
    refresh_errors = []
    if not args.cached:
        try:
            refresh_errors = cache.request(module, explicit=args.refresh)
        except OSError:
            refresh_errors = ["cache or refresh worker unavailable"]
    result = snapshot(module, cache.load(module), args)
    values = {**result, **result["data"]}
    if args.get is not None or args.format is not None:
        missing = [field for field in sorted(requested) if values[field] is None]
        if missing:
            detail = "; ".join(refresh_errors) if args.refresh and refresh_errors else "use --refresh for diagnostics"
            print(command + ": unavailable fields: " + ", ".join(missing) + "; " + detail, file=sys.stderr)
            return 1
        values = {name: scalar(value) for name, value in values.items()}
        output = values[args.get] if args.get is not None else args.format.format_map(values)
    elif args.json:
        output = json.dumps(result, ensure_ascii=True, allow_nan=False)
    elif args.text:
        output = result["text"]
    elif args.both:
        output = result["icon"] + " " + result["text"]
    else:
        output = result["icon"]
    print(output, end="" if args.no_newline else "\n")
    if args.refresh and refresh_errors:
        print(command + ": " + "; ".join(refresh_errors), file=sys.stderr)
        return 1
    return 0
