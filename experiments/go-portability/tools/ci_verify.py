#!/usr/bin/env python3
"""Collect bounded native Linux CI evidence using the existing verifier."""

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

import verify


def sanitized(text):
    text = text.replace(str(verify.REPO), "<checkout>")
    temporary = re.escape(str(Path(os.environ["RUNNER_TEMP"]).resolve()))
    return re.sub(temporary + r"/dots-portability-work-[^/\s]+", "<work>", text)


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def main():
    if sys.flags.optimize:
        raise RuntimeError("CI verification requires unoptimized Python")
    if (os.environ.get("GITHUB_ACTIONS"), os.environ.get("RUNNER_OS"), os.environ.get("RUNNER_ARCH")) != ("true", "Linux", "X64"):
        raise RuntimeError("This collector requires a native Linux/X64 GitHub Actions runner")
    temporary = Path(os.environ["RUNNER_TEMP"]).resolve()
    output = temporary / "dots-linux-evidence"
    if output.is_relative_to(verify.REPO):
        raise RuntimeError("CI evidence must stay outside the checkout")
    output.mkdir(mode=0o700)
    env = {"PATH": os.environ["PATH"], "TMPDIR": str(temporary),
           "PYTHONDONTWRITEBYTECODE": "1", "LANG": "C.UTF-8", "GIT_OPTIONAL_LOCKS": "0"}

    def capture(args):
        return subprocess.run(args, cwd=verify.REPO, env=env, capture_output=True,
                              text=True, check=True, timeout=30).stdout.strip()

    fingerprints = verify.source_fingerprints()
    commit = capture(["git", "rev-parse", "HEAD"])
    if commit != os.environ["GITHUB_SHA"]:
        raise RuntimeError("Checked-out commit differs from workflow identity")
    for name, digest in fingerprints.items():
        data = (verify.REPO / name).read_bytes()
        if hashlib.sha256(data).hexdigest() != digest:
            raise RuntimeError("Input changed during source capture")
        target = output / "tested-source" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    identity = {"commit": commit, "sha256": fingerprints,
                "source_status": capture(["git", "status", "--porcelain=v1", "--", *fingerprints])}
    write_json(output / "tested-source.json", identity)
    if identity["source_status"]:
        raise RuntimeError("CI inputs are dirty before verification")

    runner = {key: os.environ.get(key, "unknown") for key in
              ("RUNNER_OS", "RUNNER_ARCH", "RUNNER_ENVIRONMENT", "ImageOS", "ImageVersion",
               "GITHUB_REPOSITORY", "GITHUB_REF", "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT")}
    runner.update(kernel=os.uname().release, machine=os.uname().machine, cpu_count=os.cpu_count(),
                  available_cpus=len(os.sched_getaffinity(0)), python=sys.version.split()[0],
                  filesystem=capture(["stat", "-f", "-c", "%T", str(output)]),
                  hyperfine=capture(["hyperfine", "--version"]),
                  readelf=capture(["readelf", "--version"]).splitlines()[0])
    runner["os_release"] = {}
    for line in Path("/etc/os-release").read_text().splitlines():
        key, _, value = line.partition("=")
        if key in ("ID", "VERSION_ID", "PRETTY_NAME"):
            runner["os_release"][key] = value.strip('"')
    runner["cpu_model"] = next((line.split(":", 1)[1].strip() for line in Path("/proc/cpuinfo").read_text().splitlines()
                                if line.startswith("model name")), "unknown")
    runner["limitations"] = "Linux CI measurements; no controlled cold cache, CPU frequency, co-tenancy, power or thermal state; not a desktop hardware baseline"
    write_json(output / "runner.json", runner)
    print(json.dumps(runner, indent=2), flush=True)
    results = []
    hashes = []
    for mode in ("check", "bench"):
        command = [sys.executable, "-B", str(verify.MODULE / "tools" / "verify.py"), mode]
        proc = subprocess.run(command, cwd=verify.REPO, env=env, capture_output=True, text=True, timeout=900)
        (output / (mode + ".stdout.log")).write_text(sanitized(proc.stdout), encoding="utf-8")
        (output / (mode + ".stderr.log")).write_text(sanitized(proc.stderr), encoding="utf-8")
        results.append({"mode": mode, "command": "python3 -B experiments/go-portability/tools/verify.py " + mode,
                        "exit_code": proc.returncode})
        write_json(output / "results.json", results)
        print(sanitized(proc.stderr), flush=True)
        if proc.returncode:
            raise RuntimeError(mode + " failed; inspect the retained log")
        binary = Path(proc.stdout.strip()).resolve()
        artifact = binary.parent.parent
        if artifact.parent != temporary or not artifact.name.startswith("dots-spike-artifact-") or binary.name != "dots-spike":
            raise RuntimeError("Unexpected artifact location")
        metadata = json.loads((artifact / "evidence.json").read_text())
        if metadata["native_target"] != "linux/amd64" or not metadata["executed_natively"]:
            raise RuntimeError("Evidence does not represent native Linux/AMD64 execution")
        if metadata["source_sha256"] != fingerprints or hashlib.sha256(binary.read_bytes()).hexdigest() != metadata["sha256"]:
            raise RuntimeError("Source or binary identity differs from recorded evidence")
        shutil.copytree(artifact, output / mode)
        hashes.append(metadata["sha256"])
        print(mode + " binary SHA-256: " + metadata["sha256"], flush=True)
        if mode == "bench":
            write_json(output / "raw-timings.json", metadata["benchmark"]["batches"])
            print(json.dumps(metadata["benchmark"]["summary"], indent=2), flush=True)
    if len(set(hashes)) != 1 or verify.source_fingerprints() != fingerprints:
        raise RuntimeError("Source or native binary changed between check and benchmark")
    result = subprocess.run(["git", "diff", "--check"], cwd=verify.REPO, env=env, capture_output=True, text=True, check=True)
    (output / "whitespace.log").write_text(sanitized(result.stdout + result.stderr))
    final_status = capture(["git", "status", "--porcelain=v1", "--", *fingerprints])
    if final_status:
        raise RuntimeError("CI inputs changed during verification")
    write_json(output / "artifact-sha256.json", {
        str(path.relative_to(output)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(output.rglob("*")) if path.is_file()
    })
    write_json(output / "summary.json", {"passed": True, "commit": commit, "native_target": "linux/amd64",
               "binary_sha256": hashes[0], "recorded_runs": results, "source_unchanged": True})
    print("Native Linux validation and evidence collection passed.", flush=True)


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, subprocess.SubprocessError) as error:
        print(f"Linux CI verification failed: {error}", file=sys.stderr)
        sys.exit(1)
