#!/usr/bin/env python3
"""Preview or journal a bounded configs -> config symlink migration."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys


def atomic_json(path, value):
    temporary = path.with_name(path.name + ".new")
    with temporary.open("x") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    flush(path.parent)


def flush(path):
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def inventory(home, repo):
    result = []
    mappings = [(repo / prefix / "configs", repo / prefix / "config") for prefix in (".", "androidots", "windots")]
    # Include the public ~/dots alias without resolving away the old path text.
    if (home / "dots").is_symlink() and (home / "dots").resolve() == repo.resolve():
        mappings += [(home / "dots" / prefix / "configs", home / "dots" / prefix / "config") for prefix in (".", "androidots", "windots")]
    for top in (home, home / ".config", home / ".local/bin", home / ".termux"):
        if not top.is_dir():
            continue
        # Inspect directory entries only. Never follow directory links recursively.
        for path in sorted(top.iterdir()):
            if not path.is_symlink():
                continue
            old = os.readlink(path)
            absolute = Path(os.path.abspath(path.parent / old))
            for before, after in mappings:
                if absolute.is_relative_to(before):
                    new_absolute = after / absolute.relative_to(before)
                    new = str(new_absolute) if os.path.isabs(old) else os.path.relpath(new_absolute, path.parent)
                    if not new_absolute.exists() or new_absolute.resolve() != path.resolve():
                        raise ValueError(f"replacement does not preserve target: {path}")
                    result.append(dict(path=str(path), old=old, new=new, done=False))
                    break
    return result


def check(row, expected):
    p = Path(row["path"])
    if not p.is_symlink() or os.readlink(p) != expected:
        raise ValueError(f"link drift: {p}")


def replace(row, expected, wanted):
    check(row, expected)
    path = Path(row["path"])
    temp = path.with_name(path.name + ".dots-migrate-new")
    os.symlink(wanted, temp)  # Exclusive creation, never clobber a staging object.
    try:
        check(row, expected)
        os.replace(temp, path)
        flush(path.parent)
    finally:
        if temp.is_symlink():
            temp.unlink()


def rollback(doc, journal):
    for row in reversed(doc["links"]):
        path = Path(row["path"])
        if path.is_symlink() and os.readlink(path) == row["new"]:
            replace(row, row["new"], row["old"])
        else:
            check(row, row["old"])
        row["done"] = False
        atomic_json(journal, doc)
    doc["status"] = "rolled-back"
    atomic_json(journal, doc)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--home", type=Path, required=True)
    p.add_argument("--repo", type=Path, required=True)
    p.add_argument("--apply", action="store_true")
    p.add_argument("--rollback", action="store_true")
    p.add_argument("--journal", type=Path)
    args = p.parse_args()
    if args.apply and args.rollback:
        p.error("choose apply or rollback")
    if args.apply or args.rollback:
        if not args.journal or not args.journal.is_absolute():
            p.error("mutation requires an absolute --journal path")
    if args.rollback:
        if args.journal.is_symlink():
            raise ValueError("journal must be a regular file")
        doc = json.loads(args.journal.read_text())
        if doc.get("home") != str(args.home.absolute()) or doc.get("repo") != str(args.repo.resolve()):
            raise ValueError("journal roots do not match")
        rollback(doc, args.journal)
        return
    rows = inventory(args.home.absolute(), args.repo.resolve())
    doc = dict(schema=1, home=str(args.home.absolute()), repo=str(args.repo.resolve()), status="prepared", links=rows)
    if not args.apply:
        print(json.dumps(doc, indent=2))
        return
    if args.journal.exists() or args.journal.is_symlink():
        raise ValueError("journal already exists")
    for row in rows:
        check(row, row["old"])
    atomic_json(args.journal, doc)
    try:
        for row in rows:
            replace(row, row["old"], row["new"])
            row["done"] = True
            atomic_json(args.journal, doc)
        doc["status"] = "committed"
        atomic_json(args.journal, doc)
    except BaseException:
        rollback(doc, args.journal)
        raise
    print(f"Migrated {len(rows)} links; recovery journal: {args.journal}")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError) as exc:
        print(f"config migration: {exc}", file=sys.stderr)
        sys.exit(1)
