#!/usr/bin/env python3
"""Versioned file metadata and read-only filesystem observation for dots."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile

ID = re.compile(r"^[a-z][a-z0-9_-]*$")
PLATFORMS = {"termux", "linux", "wsl", "windows"}


def read_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 4 * 1024 * 1024:
        raise ValueError(f"invalid catalog file: {path}")
    result = json.loads(path.read_text(), object_pairs_hook=unique)
    if not isinstance(result, dict) or type(result.get("schema")) is not int or result.get("schema") != 1:
        raise ValueError(f"unsupported catalog schema: {path}")
    return result


def relative(value):
    if not isinstance(value, str) or not value or any(ord(c) < 32 for c in value):
        raise ValueError("invalid relative path")
    p = Path(value)
    if p.is_absolute() or ".." in p.parts:
        raise ValueError(f"source path must stay in its repository: {value}")
    return p


def platform():
    if os.name == "nt":
        return "windows"
    if os.environ.get("TERMUX_VERSION") and os.environ.get("PREFIX", "").endswith("/usr"):
        return "termux"
    if os.environ.get("WSL_DISTRO_NAME") or "microsoft" in os.uname().release.lower():
        return "wsl"
    return "linux"


def atomic_json(path, data):
    fd, name = tempfile.mkstemp(prefix=".files-", dir=path.parent)
    try:
        os.fchmod(fd, stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o644)
        with os.fdopen(fd, "w") as out:
            json.dump(data, out, indent=2, ensure_ascii=False)
            out.write("\n")
            out.flush()
            os.fsync(out.fileno())
        os.replace(name, path)
        fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    finally:
        if os.path.exists(name):
            os.unlink(name)


class Catalog:
    def __init__(self, root, selected):
        self.root = root.resolve()
        if (self.root / ".dots").is_symlink():
            raise ValueError("catalog directory must not be a symlink")
        self.platform = selected
        self.sources = []
        seen = set()
        for row in read_json(self.root / ".dots/sources.json").get("sources", []):
            if not ID.fullmatch(row["id"]) or row["id"] in seen:
                raise ValueError("duplicate or invalid repository ID")
            seen.add(row["id"])
            path = self.root / relative(row["path"])
            if not path.resolve().is_relative_to(self.root):
                raise ValueError("repository escapes dots root")
            row = dict(row, root=str(path), status="available")
            if row.get("excluded"):
                row["status"] = "excluded"
            elif not path.is_dir() or not (path / ".dots/files.json").is_file():
                row["status"] = "unavailable"
            self.sources.append(row)

    def applicable(self, platforms):
        if not isinstance(platforms, list) or not platforms or not set(platforms) <= PLATFORMS:
            raise ValueError("invalid platforms")
        return self.platform in platforms

    def manifest(self, source):
        if (Path(source["root"]) / ".dots").is_symlink():
            raise ValueError("catalog directory must not be a symlink")
        doc = read_json(Path(source["root"]) / ".dots/files.json")
        if doc.get("repository") != source["id"] or not isinstance(doc.get("resources"), list):
            raise ValueError("catalog repository identity mismatch")
        seen = set()
        for row in doc["resources"]:
            if not ID.fullmatch(row.get("id", "")) or row["id"] in seen:
                raise ValueError("duplicate or invalid resource ID")
            seen.add(row["id"])
            relative(row["source"])
            self.applicable(row["platforms"])
            if row.get("strategy") not in ("link", "directory-link", "copy"):
                raise ValueError("invalid file strategy")
            for field in ("app", "category"):
                if not ID.fullmatch(row.get(field, "")):
                    raise ValueError(f"invalid {field}")
            if row.get("target") is not None:
                self.target(row["target"])
            for key in row.get("replaces", []):
                if not re.fullmatch(r"[a-z][a-z0-9_-]*:[a-z][a-z0-9_-]*", key):
                    raise ValueError("invalid replacement ID")
        return doc

    def target(self, value):
        if not isinstance(value, str) or any(ord(c) < 32 for c in value):
            raise ValueError("invalid target")
        home = os.environ.get("HOME", "")
        tokens = {"HOME": home, "CONFIG": os.environ.get("XDG_CONFIG_HOME") or home + "/.config",
                  "BIN": home + "/.local/bin", "TERMUX": home + "/.termux"}
        match = re.fullmatch(r"\$\{(HOME|CONFIG|BIN|TERMUX)\}(?:/(.*))?", value)
        if not match:
            raise ValueError("target must start with ${HOME}, ${CONFIG}, ${BIN}, or ${TERMUX}")
        suffix = relative(match[2]) if match[2] else Path(".")
        base = tokens[match[1]]
        if not home or not Path(base).is_absolute():
            raise ValueError("absolute HOME and target roots required")
        if match[1] == "TERMUX" and self.platform != "termux":
            return None
        if self.platform == "windows":
            return None  # No native Windows destination adapter yet.
        return str(Path(base) / suffix)

    def records(self):
        result = []
        for source in self.sources:
            if source["status"] != "available":
                continue
            for item in self.manifest(source)["resources"]:
                row = dict(item)
                row.update(id=source["id"] + ":" + item["id"], repository=source["id"], tracked=True)
                row["source"] = str(Path(source["root"]) / item["source"])
                row["target_spec"] = item.get("target")
                row["target"] = self.target(item["target"]) if item.get("target") else None
                row["applicable"] = self.applicable(item["platforms"]) and self.applicable(source["platforms"])
                row["status"] = self.observe(row)
                result.append(row)
        by_id = {r["id"]: r for r in result}
        claims = {}
        for row in result:
            if row["applicable"] and row["target"]:
                # Normalize parent aliases but preserve final link identity.
                target = Path(row["target"])
                key = str(target.parent.resolve() / target.name)
                claims.setdefault(key, []).append(row)
        for rows in claims.values():
            if len(rows) < 2:
                continue
            winners = [r for r in rows if set(r.get("replaces", [])) >= {x["id"] for x in rows if x != r}]
            if len(winners) == 1:
                for row in rows:
                    if row is not winners[0]:
                        row["status"] = "replaced"
                        row["replaced_by"] = winners[0]["id"]
            else:
                for row in rows:
                    row["status"] = "conflict"
                    row["conflicts"] = sorted(x["id"] for x in rows if x != row)
        for row in result:
            if any(x not in by_id for x in row.get("replaces", [])):
                row["replacement_unavailable"] = True
        # Directory ownership conflicts with nested targets, even if the
        # directory is already linked into the source repository.
        active = [r for r in result if r["applicable"] and r["target"] and r["status"] != "replaced"]
        directories = {}
        for row in active:
            if row["strategy"] == "directory-link":
                directories.setdefault(Path(row["target"]), []).append(row)
        for child in active:
            for parent in Path(child["target"]).parents:
                for owner in directories.get(parent, []):
                    for row, other in ((owner, child), (child, owner)):
                        row["status"] = "conflict"
                        row["conflicts"] = sorted(set(row.get("conflicts", [])) | {other["id"]})
        return result

    @staticmethod
    def observe(row):
        src = Path(row["source"])
        if not src.exists():
            return "source-broken-link" if src.is_symlink() else "source-missing"
        if not row["applicable"]:
            return "inactive-platform"
        if not row["target_spec"]:
            return "unmapped"
        if row["target"] is None:
            return "unsupported-platform"
        target = Path(row["target"])
        if target.is_symlink():
            if not target.exists():
                return "broken-link"
            return "linked" if target.resolve() == src.resolve() else "linked-elsewhere"
        if not target.exists():
            return "missing"
        return "existing-directory" if target.is_dir() else "existing-file"

    def discover(self):
        tracked = self.records()
        covered = [(Path(r["source"]), r["strategy"] == "directory-link") for r in tracked]
        result = []
        for source in self.sources:
            if source["status"] != "available":
                continue
            root = Path(source["root"])
            child_roots = {Path(x["root"]) for x in self.sources if x != source}
            # Git supplies exclusions without executing hooks or traversing submodules.
            git = subprocess.run(["git", "-C", str(root), "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
                                 capture_output=True, check=True)
            candidates = set(os.fsdecode(x) for x in git.stdout.split(b"\0") if x)
            scopes = [relative(x) for x in source.get("roots", [])]
            for rel in sorted(candidates):
                path = root / rel
                if not any(Path(rel).is_relative_to(s) for s in scopes):
                    continue
                if any(path == c or path.is_relative_to(c) for c in child_roots):
                    continue
                # Parent directory links include the temporary configs alias.
                if any(p.is_symlink() for p in path.parents if p != root and p.is_relative_to(root)):
                    continue
                if not path.exists() and not path.is_symlink():
                    continue
                if path.is_dir() and ((path / ".git").exists() or (path / ".git").is_file()):
                    continue
                if any(path == p or directory and path.is_relative_to(p) for p, directory in covered):
                    continue
                parts = Path(rel).parts
                result.append(dict(id=source["id"] + ":" + rel, source=str(path), target=None,
                                   repository=source["id"], app=parts[1] if parts[0]=="config" and len(parts)>1 else parts[0],
                                   category="config" if parts[0] in ("config", "termux") else "script",
                                   platforms=source["platforms"], applicable=self.applicable(source["platforms"]),
                                   status="discovered", tracked=False))
        return result

    def track(self, args):
        source = next((s for s in self.sources if s["id"] == args.repo), None)
        if not source or source["status"] != "available":
            raise ValueError("select an available repository with --repo")
        root = Path(source["root"])
        self.manifest(source)  # Validate the directory before opening its lock.
        rel = relative(args.value)
        path = root / rel
        if not path.exists() and not path.is_symlink():
            raise ValueError("source does not exist")
        if not path.parent.resolve().is_relative_to(root.resolve()):
            raise ValueError("source parent escapes repository")
        for child in self.sources:
            c = Path(child["root"])
            if c != root and c.is_relative_to(root) and (path == c or path.is_relative_to(c)):
                raise ValueError("track this source in its owning repository")
        if not args.id or not args.app or not args.category:
            raise ValueError("track requires --id, --app and --category")
        if path.is_dir() and args.strategy != "directory-link":
            raise ValueError("whole directories require --strategy directory-link")
        row = dict(id=args.id, source=str(rel), app=args.app, category=args.category,
                   platforms=args.platforms or source["platforms"], target=args.target, strategy=args.strategy)
        if args.replaces:
            row["replaces"] = args.replaces
        file = root / ".dots/files.json"
        lock = file.with_suffix(".lock")
        fd = os.open(lock, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "a") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            doc = self.manifest(source)
            old = next((x for x in doc["resources"] if x["id"] == args.id), None)
            if old == row:
                return row
            if old and not args.update:
                raise ValueError("record exists; use --update to change its metadata")
            updated = dict(doc, resources=sorted([x for x in doc["resources"] if x["id"] != args.id] + [row], key=lambda r:r["id"]))
            # Validate candidate using the same reader before replacing the catalog.
            if not ID.fullmatch(args.id) or not ID.fullmatch(args.app) or not ID.fullmatch(args.category):
                raise ValueError("invalid resource identifiers")
            self.applicable(row["platforms"])
            if args.target:
                self.target(args.target)
            if args.replaces and any(not re.fullmatch(r"[a-z][a-z0-9_-]*:[a-z][a-z0-9_-]*", x) for x in args.replaces):
                raise ValueError("invalid replacement ID")
            atomic_json(file, updated)
        return row


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["sources", "discover", "list", "locate", "show", "source", "target", "track"])
    parser.add_argument("value", nargs="?")
    parser.add_argument("--repo")
    parser.add_argument("--app")
    parser.add_argument("--category")
    parser.add_argument("--status")
    parser.add_argument("--platform", choices=sorted(PLATFORMS), default=platform())
    parser.add_argument("--all-platforms", action="store_true")
    parser.add_argument("--sort", choices=["id", "app", "repository", "source", "status"], default="id")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--id")
    parser.add_argument("--target")
    parser.add_argument("--platforms", nargs="+", choices=sorted(PLATFORMS))
    parser.add_argument("--strategy", choices=["link", "copy", "directory-link"], default="link")
    parser.add_argument("--replaces", action="append")
    parser.add_argument("--update", action="store_true")
    args = parser.parse_args(argv)
    cat = Catalog(Path(os.environ.get("DOTS") or Path(__file__).resolve().parents[3]), args.platform)
    if args.action in ("locate", "show", "source", "target", "track") and not args.value:
        parser.error("this action requires a query, resource ID, or source")
    if args.action in ("sources", "list", "discover") and args.value:
        parser.error("this action takes options only")
    if args.action == "sources":
        rows = [s for s in cat.sources if not args.repo or s["id"] == args.repo]
    elif args.action == "track":
        rows = [cat.track(args)]
    else:
        rows = cat.discover() if args.action == "discover" else cat.records()
        if args.action == "locate":
            rows += cat.discover()
            q = args.value.casefold()
            rows = [r for r in rows if any(q in str(r.get(k, "")).casefold() for k in ("id", "source", "target", "app"))]
        if args.action in ("show", "source", "target"):
            rows = [r for r in rows if r["id"] == args.value]
            if len(rows) != 1:
                raise ValueError("resource ID not found")
        else:
            rows = [r for r in rows if args.all_platforms or r["applicable"]]
        for option, field in ((args.repo, "repository"), (args.app, "app"), (args.category, "category"), (args.status, "status")):
            if option:
                rows = [r for r in rows if r.get(field) == option]
        if args.action in ("show", "source", "target") and len(rows) != 1:
            raise ValueError("resource does not match the requested filters")
        rows.sort(key=lambda r:(str(r.get(args.sort, "")), r["id"]))
    if args.json:
        print(json.dumps(dict(schema=1, platform=args.platform, resources=rows if args.action!="sources" else [], sources=rows if args.action=="sources" else cat.sources), ensure_ascii=False))
    elif args.action in ("source", "target"):
        value = rows[0].get(args.action)
        if value is None:
            raise ValueError("resource has no resolved target")
        print(value)
    elif args.action == "show":
        for key, value in rows[0].items():
            print(f"{key}: {value}")
    elif args.action == "sources":
        for row in rows:
            print("\t".join((row["id"], row["status"], row["root"], ",".join(row["platforms"]))))
    else:
        for r in rows:
            print("\t".join(str(r.get(k, "")) for k in ("id", "status", "source", "target")))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        print(f"dots files: {exc}", file=sys.stderr)
        sys.exit(1)
