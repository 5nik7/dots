#!/usr/bin/env python3
"""Build/test the spike with an isolated toolchain environment; never install it."""

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from urllib.parse import unquote, urlsplit

MODULE = Path(__file__).resolve().parents[1]
REPO = MODULE.parents[1]
BUILD_FLAGS = ["-trimpath", "-buildvcs=false", "-mod=readonly"]


def tool(name):
    found = shutil.which(name)
    if not found:
        raise RuntimeError(f"Missing prerequisite: {name} must already be installed and on PATH; nothing was installed.")
    return str(Path(found).absolute())


def run(args, *, cwd, env, capture=False):
    print("+ " + shlex.join(map(str, args)), file=sys.stderr, flush=True)
    return subprocess.run(
        list(map(str, args)), cwd=cwd, env=env, check=True, text=True,
        stdout=subprocess.PIPE if capture else sys.stderr, stderr=None, timeout=600,
    )


def source_copy(destination):
    destination.mkdir(parents=True)
    paths = [MODULE / "go.mod"]
    for directory in ("cmd", "internal", "tests"):
        paths.extend(sorted((MODULE / directory).rglob("*.go")))
    for path in paths:
        if path.is_symlink() or any(p.is_symlink() for p in path.parents if p != MODULE):
            raise RuntimeError("Refusing symlinked experimental source")
        target = destination / path.relative_to(MODULE)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)


def environments(root, go):
    names = ("home", "config", "data", "state", "cache", "tmp", "bin", "gopath", "tooltmp", "runtime/repo", "runtime/bin", "runtime/usr/bin")
    for name in names:
        (root / name).mkdir(parents=True, exist_ok=True)
    # This is a new child environment, not a modification of the active shell.
    env = {
        "PATH": str(Path(go).parent), "HOME": str(root / "home"),
        "XDG_CONFIG_HOME": str(root / "config"), "XDG_DATA_HOME": str(root / "data"),
        "XDG_STATE_HOME": str(root / "state"), "XDG_CACHE_HOME": str(root / "cache"),
        "TMPDIR": str(root / "tmp"), "TMP": str(root / "tmp"), "TEMP": str(root / "tmp"),
        "USERPROFILE": str(root / "home"), "APPDATA": str(root / "config"), "LOCALAPPDATA": str(root / "data"),
        "GOENV": "off", "GOWORK": "off", "GOTOOLCHAIN": "local", "GOPROXY": "off", "GOSUMDB": "off",
        "GOPATH": str(root / "gopath"), "GOMODCACHE": str(root / "cache" / "gomod"),
        "GOCACHE": str(root / "cache" / "gobuild"), "GOTMPDIR": str(root / "tooltmp"),
        "CGO_ENABLED": "0", "GOFLAGS": "-mod=readonly -buildvcs=false", "GIT_OPTIONAL_LOCKS": "0",
        "DOTS": str(root / "runtime" / "repo"), "NO_COLOR": "1", "LANG": "C.UTF-8",
    }
    for key in ("PREFIX", "TERMUX_VERSION", "SystemRoot", "WINDIR"):
        if key in os.environ:
            env[key] = os.environ[key]
    child = dict(env, PATH="", PREFIX=str(root / "runtime" / "usr"), TERMUX_VERSION="fixture")
    # Do not expose Go cache/config variables to the executable under test.
    for key in list(child):
        if key.startswith("GO") or key.startswith("GIT_"):
            del child[key]
    return env, child


def snapshot(paths):
    result = {}
    for base in paths:
        for path in [base, *sorted(base.rglob("*"))]:
            info = path.lstat()
            content = os.readlink(path) if path.is_symlink() else None
            if stat.S_ISREG(info.st_mode):
                content = hashlib.sha256(path.read_bytes()).hexdigest()
            result[str(path)] = (info.st_mode, info.st_size, info.st_mtime_ns, content)
    return result


def cli_checks(binary, root, env):
    targets = [root / name for name in ("home", "config", "data", "state", "cache", "runtime", "tmp")]
    logo = Path(env["DOTS"]) / "logo.txt"
    logo.write_text("FIXTURE LOGO\n", encoding="utf-8")
    before = snapshot(targets)
    cases = [([], 0), (["help"], 0), (["-h"], 0), (["--help"], 0), (["--version"], 0),
             (["doctor"], 0), (["doctor", "--json"], 0), (["doctor", "--help"], 0),
             (["apply"], 2), (["doctor", "--json", "TOP_SECRET_ARGUMENT"], 2)]
    secret_env = dict(env, TOP_SECRET="TOP_SECRET_VALUE")
    for args, expected in cases:
        proc = subprocess.run([str(binary), *args], env=secret_env, cwd=root / "runtime", capture_output=True, text=True, timeout=10)
        assert proc.returncode == expected, (args, proc.returncode, proc.stderr)
        assert (not proc.stderr) if expected == 0 else (not proc.stdout and proc.stderr)
        assert "TOP_SECRET" not in proc.stdout + proc.stderr
        if args == ["--version"]:
            assert "FIXTURE LOGO" not in proc.stdout and proc.stdout.startswith("dots-spike 0.0.0-spike ")
        elif args == ["doctor", "--json"]:
            report = json.loads(proc.stdout)
            assert set(report) == {"schema_version", "platform", "os", "architecture", "go_version", "evidence", "paths", "capabilities", "warnings"}
            assert report["schema_version"] == 1 and all(v == "not_probed" for v in report["capabilities"].values())
            assert (report["platform"], report["os"], report["architecture"]) == ("termux", "android", "arm64")
            assert "FIXTURE LOGO" not in proc.stdout and "\x1b" not in proc.stdout
        elif not args or args in (["help"], ["-h"], ["--help"], ["doctor", "--help"]):
            assert proc.stdout.startswith("FIXTURE LOGO\n\n")
    assert before == snapshot(targets), "Read-only CLI changed fixture roots"

    # Optional-logo failure modes, including a FIFO that must never be opened.
    logo.unlink()
    modes = ["missing", "empty", "directory", "unreadable", "oversize", "broken-link"]
    if hasattr(os, "mkfifo"):
        modes.append("fifo")
    for mode in modes:
        if mode == "empty": logo.touch()
        elif mode == "directory": logo.mkdir()
        elif mode == "unreadable":
            logo.write_text("HIDDEN LOGO", encoding="utf-8")
            logo.chmod(0)
        elif mode == "oversize": logo.write_bytes(b"x" * 65537)
        elif mode == "broken-link": logo.symlink_to("missing-logo-source")
        elif mode == "fifo": os.mkfifo(logo, 0o600)
        proc = subprocess.run([str(binary), "--help"], env=env, cwd=root, capture_output=True, text=True, timeout=10)
        assert proc.returncode == 0 and "Usage:" in proc.stdout and not proc.stderr, mode
        if mode != "unreadable" or not os.access(logo, os.R_OK):
            assert proc.stdout.startswith("dots-spike -"), mode
        if logo.is_dir(): logo.rmdir()
        elif logo.exists() or logo.is_symlink():
            if mode == "unreadable": logo.chmod(0o600)
            logo.unlink()

    # Executable-relative fallback follows a symlink without a repository walk.
    fallback = root / "logo.txt"
    fallback.write_text("FALLBACK LOGO", encoding="utf-8")
    alias = root / "runtime" / "bin" / "alias"
    alias.symlink_to(binary)
    without_dots = {key: value for key, value in env.items() if key != "DOTS"}
    proc = subprocess.run([str(alias), "help"], env=without_dots, cwd=root / "runtime", capture_output=True, text=True, timeout=10)
    assert proc.returncode == 0 and proc.stdout.startswith("FALLBACK LOGO\n\n")
    logo.write_text("UPDATED LOGO", encoding="utf-8")
    proc = subprocess.run([str(binary), "--help"], env=env, cwd=root, capture_output=True, text=True, timeout=10)
    assert proc.stdout.startswith("UPDATED LOGO\n\n"), "logo must be loaded dynamically"
    print(f"CLI process checks passed ({len(cases)} requests, {len(modes)} optional-logo cases, symlink fallback and reload).", file=sys.stderr)


def doc_checks():
    files = [REPO / "README.md", REPO / "AGENTS.md"]
    for directory in ("agents", "docs", "plans"):
        files.extend(sorted((REPO / directory).rglob("*.md")))
    checked = 0
    for path in files:
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
            parsed = urlsplit(target.strip("<>"))
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            if not (path.parent / unquote(parsed.path)).exists():
                raise RuntimeError(f"Broken relative Markdown link: {path.relative_to(REPO)} -> {target}")
            checked += 1
    print(f"Relative Markdown links passed ({checked} links in {len(files)} files).", file=sys.stderr)


def build(go, source, root, env, name="dots-spike", target=None):
    binary = root / "bin" / name
    build_env = dict(env)
    if target:
        build_env.update(GOOS=target[0], GOARCH=target[1])
    run([go, "build", *BUILD_FLAGS, "-o", binary, "./cmd/dots-spike"], cwd=source, env=build_env)
    return binary


def benchmark(binary, root, env, hyperfine):
    # The logo used in measurements is copied verbatim from the public source.
    shutil.copyfile(REPO / "logo.txt", Path(env["DOTS"]) / "logo.txt")
    first = {}
    for argument in ("--help", "--version"):
        start = time.perf_counter_ns()
        subprocess.run([str(binary), argument], env=env, cwd=root, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True, timeout=10)
        first[argument] = (time.perf_counter_ns() - start) / 1e9
    batches = []
    for batch in range(3):
        output = root / f"timings-{batch}.json"
        args = ("--help", "--version") if batch % 2 == 0 else ("--version", "--help")
        run([hyperfine, "--shell=none", "--warmup", "20", "--runs", "200", "--export-json", output,
             *[shlex.join([str(binary), arg]) for arg in args]], cwd=root, env=env)
        batches.append(json.loads(output.read_text(encoding="utf-8")))
    summary = {}
    for arg in ("--help", "--version"):
        values = sorted(t for batch in batches for result in batch["results"] if result["command"].endswith(arg) for t in result["times"])
        summary[arg] = {"samples": len(values), "median_ms": (values[299] + values[300]) * 500,
                        "p95_ms": values[569] * 1000, "min_ms": values[0] * 1000, "max_ms": values[-1] * 1000}
    return {"method": "hyperfine --shell=none; 3 batches, 20 warmups and 200 samples per command per batch; alternating order; stdout discarded",
            "cold_cache": "not measured; no cache eviction or reboot", "first_observed_seconds": first,
            "summary": summary, "batches": batches}


def main():
    if sys.flags.optimize:
        raise RuntimeError(
            "optimized Python is unsupported because it disables verification assertions; "
            "rerun without -O/-OO and with PYTHONOPTIMIZE unset or 0."
        )
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("build", "check", "bench", "cross", "docs"))
    mode = parser.parse_args().mode
    if mode == "docs":
        doc_checks()
        return
    go = tool("go")
    hyperfine = tool("hyperfine") if mode == "bench" else None
    gofmt = tool("gofmt") if mode == "check" else None
    readelf = tool("readelf") if mode == "check" else None
    with tempfile.TemporaryDirectory(prefix="dots-portability-work-") as temporary:
        root = Path(temporary).resolve()
        source = root / "repo" / "module with spaces"
        source_copy(source)
        env, child = environments(root, go)
        if mode == "check":
            run([sys.executable, "-B", MODULE / "tools" / "test_verify.py"], cwd=root, env=env)
        info = json.loads(run([go, "env", "-json", "GOHOSTOS", "GOHOSTARCH", "GOVERSION"], cwd=source, env=env, capture=True).stdout)
        if info["GOHOSTOS"] != "android" or info["GOHOSTARCH"] != "arm64":
            raise RuntimeError("This runner is verified only for native Termux android/arm64; other target execution remains deferred.")
        # Explicit settings prevent the host's persistent Go configuration from
        # influencing the build. Telemetry is disabled by Go on Android.
        native = (info["GOHOSTOS"], info["GOHOSTARCH"])
        env.update(GOOS=native[0], GOARCH=native[1])
        binary = build(go, source, root, env)
        metadata = {"date_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "toolchain": info, "build_flags": BUILD_FLAGS, "cgo_enabled": 0,
                    "kernel": os.uname().release, "machine": os.uname().machine,
                    "termux_version": os.environ.get("TERMUX_VERSION", "unknown"),
                    "binary_bytes": binary.stat().st_size, "sha256": hashlib.sha256(binary.read_bytes()).hexdigest()}
        if mode == "check":
            unformatted = run([gofmt, "-l", "cmd", "internal", "tests"], cwd=source, env=env, capture=True).stdout
            if unformatted:
                raise RuntimeError("Run gofmt on the experimental Go sources:\n" + unformatted)
            # Go tests use fixture roots; process checks separately enforce an empty PATH.
            test_env = dict(env, DOTS=child["DOTS"], PREFIX=child["PREFIX"])
            run([go, "vet", "./..."], cwd=source, env=test_env)
            run([go, "test", "-count=1", "-v", "./..."], cwd=source, env=test_env)
            cli_checks(binary, root, child)
            relocated = root / "relocated" / "module"
            source_copy(relocated)
            repeat = build(go, relocated, root, env, "repeat")
            assert binary.read_bytes() == repeat.read_bytes(), "repeated relocated build differed"
            elf = run([readelf, "-l", "-d", binary], cwd=root, env=env, capture=True).stdout
            metadata["elf"] = elf
            print("ELF dependencies:", file=sys.stderr)
            print("\n".join(line for line in elf.splitlines() if "interpreter" in line or "NEEDED" in line) or "No interpreter/NEEDED entries", file=sys.stderr)
            metadata["checks"] = "Python optimization regressions, gofmt, vet, uncached Go tests, CLI processes, relocated identical rebuild, ELF inspection, Markdown links"
            doc_checks()
        elif mode == "bench":
            metadata["hyperfine"] = run([hyperfine, "--version"], cwd=root, env=env, capture=True).stdout.strip()
            metadata["benchmark"] = benchmark(binary, root, child, hyperfine)
            print(json.dumps(metadata["benchmark"]["summary"], indent=2), file=sys.stderr)
        elif mode == "cross":
            metadata["cross_compilation"] = []
            for target in (("linux", "amd64"), ("windows", "amd64")):
                name = "dots-spike-" + "-".join(target) + (".exe" if target[0] == "windows" else "")
                build(go, source, root, env, name, target)
                target_env = dict(env, GOOS=target[0], GOARCH=target[1])
                for package in ("internal/cli", "internal/platform", "tests"):
                    test_name = "-".join(target) + "-" + package.replace("/", "-") + ".test"
                    run([go, "test", "-c", "-o", root / "bin" / test_name, "./" + package], cwd=source, env=target_env)
                metadata["cross_compilation"].append({"target": "/".join(target), "built": True, "executed": False})
            print("Cross-compilation passed; foreign executables and tests were NOT run.", file=sys.stderr)
        # Retain only reviewable artifacts. The much larger tool caches and all
        # test roots are deleted by TemporaryDirectory, which owns this root.
        artifact = Path(tempfile.mkdtemp(prefix="dots-spike-artifact-")).resolve()
        shutil.copytree(root / "bin", artifact / "bin")
        shutil.copyfile(REPO / "logo.txt", artifact / "logo.txt")
        (artifact / "evidence.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
        print(f"Evidence: {artifact / 'evidence.json'}", file=sys.stderr)
        # stdout is just the executable path, suitable for command substitution.
        print(artifact / "bin" / "dots-spike")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, AssertionError, OSError, subprocess.SubprocessError) as error:
        print(f"portability verification failed: {error}", file=sys.stderr)
        sys.exit(1)
