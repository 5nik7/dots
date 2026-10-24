"""Offline build environment for the independent Anodize engine."""
import os
from pathlib import Path
import shutil


def tool(name):
    found = shutil.which(name)
    if not found:
        raise RuntimeError(f"Missing prerequisite: {name} must already be installed and on PATH; nothing was installed.")
    return str(Path(found).absolute())


def environment(root, go):
    names = ("home", "config", "data", "state", "cache", "tmp", "bin", "gopath", "tooltmp", "repo")
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
        "DOTS": str(root / "repo"), "NO_COLOR": "1", "LANG": "C.UTF-8",
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
    return env
