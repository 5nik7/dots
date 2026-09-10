#!/usr/bin/env python3
"""Build/test the permanent development core in owned roots; never install it."""

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

REPO = Path(__file__).resolve().parents[1]
MODULE = REPO
BUILD_FLAGS = ["-trimpath", "-buildvcs=false", "-mod=readonly"]


def tool(name):
    found = shutil.which(name)
    if not found:
        raise RuntimeError(f"Missing prerequisite: {name} must already be installed and on PATH; nothing was installed.")
    return str(Path(found).absolute())


def run(args, *, cwd, env, capture=False):
    print("+ " + shlex.join(map(str, args)), file=sys.stderr, flush=True)
    result = subprocess.run(
        list(map(str, args)), cwd=cwd, env=env, text=True, encoding="utf-8",
        stdout=subprocess.PIPE if capture else sys.stderr, stderr=None, timeout=600,
    )
    if result.returncode and capture:
        print(result.stdout, file=sys.stderr)
    result.check_returncode()
    return result


def source_copy(destination):
    destination.mkdir(parents=True)
    paths = [MODULE / "go.mod"]
    for directory in ("cmd", "internal", "tests"):
        paths.extend(sorted((MODULE / directory).rglob("*.go")))
    for path in paths:
        if path.is_symlink() or any(p.is_symlink() for p in path.parents if p != MODULE):
            raise RuntimeError("Refusing symlinked core source")
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
        "GOENV": "off", "GOWORK": "off", "GOTOOLCHAIN": "local", "GOPROXY": "off", "GOSUMDB": "off", "GOVCS": "*:off",
        "GOPATH": str(root / "gopath"), "GOMODCACHE": str(root / "cache" / "gomod"),
        "GOCACHE": str(root / "cache" / "gobuild"), "GOTMPDIR": str(root / "tooltmp"),
        "CGO_ENABLED": "0", "GOFLAGS": "-mod=readonly -buildvcs=false", "GIT_OPTIONAL_LOCKS": "0",
        "DOTS": str(root / "runtime" / "repo"), "NO_COLOR": "1", "LANG": "C.UTF-8",
        "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1",
    }
    for key in ("PREFIX", "TERMUX_VERSION", "SystemRoot", "WINDIR"):
        if key in os.environ:
            env[key] = os.environ[key]
    if os.name == "nt":
        env["HOMEDRIVE"], env["HOMEPATH"] = os.path.splitdrive(env["USERPROFILE"])
    # GOTELEMETRY is a read-only go env value, not an environment override.
    # Seed the owned configuration before any Go tool can collect counters.
    telemetry = root / "config" / "go" / "telemetry"
    telemetry.mkdir(parents=True)
    (telemetry / "mode").write_text("off\n", encoding="utf-8")
    child = dict(env, PATH="", PREFIX=str(root / "runtime" / "usr"), TERMUX_VERSION="fixture")
    # Do not expose Go cache/config variables to the executable under test.
    for key in list(child):
        if key.startswith("GO") or key.startswith("GIT_"):
            del child[key]
    return env, child


def configure_native(info, env, child):
    native = (info["GOHOSTOS"], info["GOHOSTARCH"])
    platforms = {("android", "arm64"): "termux", ("linux", "amd64"): "linux", ("windows", "amd64"): "windows"}
    if native not in platforms:
        raise RuntimeError("Supported native verification hosts: Termux android/arm64, Linux linux/amd64, and Windows windows/amd64; other execution remains deferred.")
    env.update(GOOS=native[0], GOARCH=native[1])
    if native[0] != "android":
        for target in (env, child):
            target.pop("PREFIX", None)
            target.pop("TERMUX_VERSION", None)
    return (platforms[native], *native)


def source_fingerprints():
    paths = [MODULE / "go.mod", REPO / "logo.txt"]
    for directory in ("cmd", "internal", "tests"):
        paths.extend((MODULE / directory).rglob("*.go"))
    paths.extend(MODULE / "tools" / name for name in ("verify_core.py", "test_verify_core.py", "ci_core.py"))
    workflow = REPO / ".github" / "workflows" / "phase-1-linux.yml"
    if workflow.exists():
        paths.append(workflow)
    result = {}
    for path in sorted(paths):
        if path.is_symlink() or any(p.is_symlink() for p in path.parents if p.is_relative_to(REPO)):
            raise RuntimeError("Refusing symlinked verification input")
        result[path.relative_to(REPO).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def redact(value, substitutions):
    """Replace paths before JSON encoding, including Windows backslashes."""
    if isinstance(value, str):
        for path, replacement in substitutions:
            value = value.replace(str(path), replacement).replace(str(path).replace("\\", "/"), replacement)
        return value
    if isinstance(value, dict):
        return {key: redact(item, substitutions) for key, item in value.items()}
    if isinstance(value, list):
        return [redact(item, substitutions) for item in value]
    return value


def executable_name(name="dots", target=None):
    windows = (target == "windows") if target is not None else os.name == "nt"
    return name + (".exe" if windows and not name.endswith(".exe") else "")


def symlink_capabilities(root, windows=None):
    """Observe only owned fixtures; unexpected errors fail verification."""
    if windows is None:
        windows = os.name == "nt"
    base = root / "symlink capabilities"
    base.mkdir()
    source = base / "source"
    source.write_text("fixture", encoding="utf-8")
    directory = base / "directory"
    directory.mkdir()
    result = {}
    for kind, target, is_dir in (("file", source, False), ("directory", directory, True)):
        link = base / (kind + " link")
        try:
            link.symlink_to(target, target_is_directory=is_dir)
        except OSError as error:
            if not windows or getattr(error, "winerror", None) not in (5, 50, 1314):
                raise
            result[kind] = {"status": "unavailable", "winerror": error.winerror, "reason": error.strerror}
        else:
            assert link.is_symlink() and link.resolve() == target.resolve()
            link.unlink()
            result[kind] = {"status": "passed"}
    return result


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


def cli_checks(binary, root, env, identity):
    links = symlink_capabilities(root)
    results = {"symlink_capabilities": links, "cases": {}}
    targets = [root / name for name in ("home", "config", "data", "state", "cache", "runtime", "tmp")]
    logo = Path(env["DOTS"]) / "logo.txt"
    logo.write_text("FIXTURE LOGO\n", encoding="utf-8")
    before = snapshot(targets)
    cases = [([], 0), (["help"], 0), (["-h"], 0), (["--help"], 0), (["--version"], 0),
             (["doctor"], 0), (["doctor", "--json"], 0), (["doctor", "--help"], 0),
             (["apply"], 2), (["doctor", "--json", "TOP_SECRET_ARGUMENT"], 2)]
    secret_env = dict(env, TOP_SECRET="TOP_SECRET_VALUE")
    for args, expected in cases:
        proc = subprocess.run([str(binary), *args], env=secret_env, cwd=root / "runtime", capture_output=True, text=True, encoding="utf-8", timeout=10)
        assert proc.returncode == expected, (args, proc.returncode, proc.stderr)
        assert (not proc.stderr) if expected == 0 else (not proc.stdout and proc.stderr)
        assert "TOP_SECRET" not in proc.stdout + proc.stderr
        if args == ["--version"]:
            assert "FIXTURE LOGO" not in proc.stdout and proc.stdout.startswith("dots 0.0.0-dev ")
        elif args == ["doctor", "--json"]:
            report = json.loads(proc.stdout)
            assert set(report) == {"schema_version", "platform", "os", "architecture", "go_version", "evidence", "paths", "capabilities", "warnings"}
            assert report["schema_version"] == 1 and all(v == "not_probed" for v in report["capabilities"].values())
            assert (report["platform"], report["os"], report["architecture"]) == identity
            assert "FIXTURE LOGO" not in proc.stdout and "\x1b" not in proc.stdout
            if identity[0] == "windows":
                assert set(report["paths"]) == {"executable"}
                assert report["warnings"] == ["Path resolution is not implemented for this platform in the spike."]
        elif args == ["doctor"]:
            assert f"Platform: {identity[0]}\n" in proc.stdout
        elif not args or args in (["help"], ["-h"], ["--help"], ["doctor", "--help"]):
            assert proc.stdout.startswith("FIXTURE LOGO\n\n")
    assert before == snapshot(targets), "Read-only CLI changed fixture roots"

    # Optional-logo failure modes, including a FIFO that must never be opened.
    logo.unlink()
    modes = ["missing", "empty", "directory", "oversize"]
    if os.name != "nt":
        modes.append("unreadable")
    else:
        results["cases"]["unreadable-logo"] = {"status": "untested", "reason": "Windows chmod does not establish ACL read denial; policy unchanged"}
        results["cases"]["fifo-logo-replacement"] = {"status": "unavailable", "reason": "Unix FIFO regression is excluded from Windows builds"}
    if links["file"]["status"] == "passed":
        modes.append("broken-link")
    else:
        results["cases"]["broken-link-logo"] = {"status": "unavailable", "reason": links["file"]}
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
        proc = subprocess.run([str(binary), "--help"], env=env, cwd=root, capture_output=True, text=True, encoding="utf-8", timeout=10)
        assert proc.returncode == 0 and "Usage:" in proc.stdout and not proc.stderr, mode
        if mode != "unreadable" or not os.access(logo, os.R_OK):
            assert proc.stdout.startswith("dots -"), mode
        results["cases"]["logo-" + mode] = {"status": "passed"}
        if logo.is_dir(): logo.rmdir()
        elif logo.exists() or logo.is_symlink():
            if mode == "unreadable": logo.chmod(0o600)
            logo.unlink()

    # Executable-relative fallback follows a symlink without a repository walk.
    fallback = root / "logo.txt"
    fallback.write_text("FALLBACK LOGO", encoding="utf-8")
    without_dots = {key: value for key, value in env.items() if key != "DOTS"}
    proc = subprocess.run([str(binary), "help"], env=without_dots, cwd=root / "runtime", capture_output=True, text=True, encoding="utf-8", timeout=10)
    assert proc.returncode == 0 and proc.stdout.startswith("FALLBACK LOGO\n\n")
    results["cases"]["direct-fallback"] = {"status": "passed"}
    if links["file"]["status"] == "passed":
        alias = root / "runtime" / "bin" / executable_name("alias")
        alias.symlink_to(binary)
        proc = subprocess.run([str(alias), "help"], env=without_dots, cwd=root / "runtime", capture_output=True, text=True, encoding="utf-8", timeout=10)
        assert proc.returncode == 0 and proc.stdout.startswith("FALLBACK LOGO\n\n")
        results["cases"]["symlink-fallback"] = {"status": "passed"}
    else:
        results["cases"]["symlink-fallback"] = {"status": "unavailable", "reason": links["file"]}
    logo.write_text("UPDATED LOGO", encoding="utf-8")
    proc = subprocess.run([str(binary), "--help"], env=env, cwd=root, capture_output=True, text=True, encoding="utf-8", timeout=10)
    assert proc.stdout.startswith("UPDATED LOGO\n\n"), "logo must be loaded dynamically"
    results["cases"].update(commands={"status": "passed", "count": len(cases)}, snapshots={"status": "passed"}, reload={"status": "passed"})
    print("CLI results: " + json.dumps(results, sort_keys=True), file=sys.stderr)
    return results


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


def build(go, source, root, env, name="dots", target=None):
    binary = root / "bin" / executable_name(name, target[0] if target else env["GOOS"])
    build_env = dict(env)
    if target:
        build_env.update(GOOS=target[0], GOARCH=target[1])
    run([go, "build", *BUILD_FLAGS, "-o", binary, "./cmd/dots"], cwd=source, env=build_env)
    return binary


def benchmark(binary, root, env, hyperfine):
    if os.name == "nt":
        # Exercise hyperfine shell_words quoting with spaces and backslashes.
        spaced = root / "benchmark bin"
        spaced.mkdir()
        relocated = spaced / binary.name
        shutil.copyfile(binary, relocated)
        binary = relocated
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
             # hyperfine --shell=none uses shell_words on Windows too.
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
    parser.add_argument("mode", choices=("build", "check", "bench", "docs"))
    mode = parser.parse_args().mode
    if mode == "docs":
        doc_checks()
        return
    fingerprints = source_fingerprints()
    go = tool("go")
    hyperfine = tool("hyperfine") if mode == "bench" else None
    gofmt = tool("gofmt") if mode == "check" else None
    inspector = tool("llvm-readobj" if os.name == "nt" else "readelf") if mode == "check" else None
    with tempfile.TemporaryDirectory(prefix="dots-core-work-") as temporary:
        root = Path(temporary).resolve()
        source = root / "repo" / "module with spaces"
        source_copy(source)
        env, child = environments(root, go)
        if mode == "check":
            run([sys.executable, "-B", MODULE / "tools" / "test_verify_core.py"], cwd=root, env=env)
        info = json.loads(run([go, "env", "-json", "GOHOSTOS", "GOHOSTARCH", "GOVERSION", "GOTELEMETRY", "GOTELEMETRYDIR"], cwd=source, env=env, capture=True).stdout)
        if info["GOTELEMETRY"] != "off" or Path(info["GOTELEMETRYDIR"]) != root / "config" / "go" / "telemetry":
            raise RuntimeError("Go telemetry is not off in the test-owned configuration directory")
        if info["GOVERSION"] != "go1.27.1":
            raise RuntimeError("Core verification requires the approved installed Go 1.27.1 toolchain; nothing was downloaded")
        identity = configure_native(info, env, child)
        binary = build(go, source, root, env)
        metadata = {"date_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "toolchain": info, "build_flags": BUILD_FLAGS, "cgo_enabled": 0,
                    "python_version": sys.version.split()[0], "source_sha256": fingerprints,
                    "native_target": "/".join(identity[1:]), "executed_natively": mode in ("check", "bench"),
                    "go_isolation": {key: env[key] for key in ("GOENV", "GOWORK", "GOTOOLCHAIN", "GOPROXY", "GOSUMDB", "GOVCS")},
                    "kernel": str(sys.getwindowsversion()) if os.name == "nt" else os.uname().release,
                    "machine": info["GOHOSTARCH"] if os.name == "nt" else os.uname().machine,
                    "termux_version": os.environ.get("TERMUX_VERSION", "unknown"),
                    "binary_bytes": binary.stat().st_size, "sha256": hashlib.sha256(binary.read_bytes()).hexdigest()}
        if mode == "check":
            unformatted = run([gofmt, "-l", "cmd", "internal", "tests"], cwd=source, env=env, capture=True).stdout
            if unformatted:
                raise RuntimeError("Run gofmt on the core Go sources:\n" + unformatted)
            # Go tests use fixture roots; process checks separately enforce an empty PATH.
            test_env = dict(env, DOTS=child["DOTS"], DOTS_CORE_TEST_BIN=str(binary))
            for key in ("PREFIX", "TERMUX_VERSION"):
                if key in child:
                    test_env[key] = child[key]
            imports = run([go, "list", "-deps", "./internal/dispatch"], cwd=source, env=env, capture=True).stdout.splitlines()
            if any(name in imports for name in ("os", "io/fs", "path/filepath", "os/exec", "net")):
                raise RuntimeError("Registry must not depend on filesystem/process/network discovery")
            metadata["registry_dependency_boundary"] = "passed: no os, io/fs, path/filepath, os/exec or net dependencies"
            run([go, "vet", "./..."], cwd=source, env=test_env)
            tested = run([go, "test", "-count=1", "-json", "./..."], cwd=source, env=test_env, capture=True)
            outcomes = []
            for line in tested.stdout.splitlines():
                event = json.loads(line)
                if event.get("Output"):
                    print(event["Output"], end="", file=sys.stderr)
                if event.get("Test") and event["Action"] in ("pass", "skip", "fail"):
                    outcomes.append({"package": event["Package"], "test": event["Test"],
                                     "status": {"pass": "passed", "skip": "unavailable", "fail": "failed"}[event["Action"]]})
            metadata["go_tests"] = outcomes
            metadata["cli"] = cli_checks(binary, root, child, identity)
            relocated = root / "relocated" / "module"
            source_copy(relocated)
            repeat = build(go, relocated, root, env, "repeat")
            assert binary.read_bytes() == repeat.read_bytes(), "repeated relocated build differed"
            if os.name == "nt":
                dependency = run([inspector, "--file-headers", "--coff-imports", binary], cwd=root, env=env, capture=True).stdout
                if "IMAGE_FILE_MACHINE_AMD64" not in dependency:
                    raise RuntimeError("PE inspector did not identify an AMD64 executable")
                imports = sorted(set(re.findall(r"Name: ([^\r\n]+\.dll)", dependency, re.IGNORECASE)))
                if not imports:
                    raise RuntimeError("PE import inspection returned no DLL names")
                metadata["dependencies"] = {"format": "PE/COFF", "imports": imports, "inspection": dependency,
                    "limitation": "Static import table only; dynamic/transitive Windows DLL loading is not enumerated"}
            else:
                dependency = run([inspector, "-l", "-d", binary], cwd=root, env=env, capture=True).stdout
                metadata["elf"] = dependency
                metadata["dependencies"] = {"format": "ELF", "inspection": dependency}
            metadata["inspector_version"] = run([inspector, "--version"], cwd=root, env=env, capture=True).stdout.strip()
            print("Runtime dependency inspection:\n" + dependency, file=sys.stderr)
            metadata["checks"] = "Python regressions, gofmt, vet, uncached native Go tests, CLI processes, relocated identical rebuild, runtime dependency inspection, Markdown links"
            doc_checks()
        elif mode == "bench":
            metadata["hyperfine"] = run([hyperfine, "--version"], cwd=root, env=env, capture=True).stdout.strip()
            metadata["benchmark"] = benchmark(binary, root, child, hyperfine)
            registry_result = run([go, "test", "-run=^$", "-bench=^BenchmarkRegistryLookup$", "-benchmem", "-benchtime=200ms", "-count=3", "./internal/dispatch"], cwd=source, env=env, capture=True).stdout
            metadata["registry_benchmark"] = {"method": "Go benchmark, 200ms adaptive iterations, 3 repetitions per registry size; in-process lookup only", "raw": registry_result}
            print(registry_result, file=sys.stderr)
            print(json.dumps(metadata["benchmark"]["summary"], indent=2), file=sys.stderr)
        # Retain only reviewable artifacts. The much larger tool caches and all
        # test roots are deleted by TemporaryDirectory, which owns this root.
        if source_fingerprints() != fingerprints:
            raise RuntimeError("Verification inputs changed during execution")
        artifact = Path(tempfile.mkdtemp(prefix="dots-core-artifact-")).resolve()
        shutil.copytree(binary.parent, artifact / "bin")
        shutil.copyfile(REPO / "logo.txt", artifact / "logo.txt")
        sanitized = json.dumps(redact(metadata, [(root, "<work>"), (REPO, "<checkout>")]), indent=2)
        (artifact / "evidence.json").write_text(sanitized + "\n", encoding="utf-8")
        print(f"Evidence: {artifact / 'evidence.json'}", file=sys.stderr)
        # stdout is just the executable path, suitable for command substitution.
        print(artifact / "bin" / binary.name)


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, AssertionError, OSError, subprocess.SubprocessError) as error:
        print(f"core verification failed: {error}", file=sys.stderr)
        sys.exit(1)
