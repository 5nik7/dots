"""Atomic private cache and one-shot, flock-serialized refresh workers."""

import fcntl
import json
import math
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
import time

from .providers import GATED, PROVIDERS, STREAMS, TTL, ProviderError, collect


MAX_AGE = 300


def boot_id():
    try:
        return Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    except OSError:
        # Without a trustworthy boot identity, never reuse data as fresh.
        return None


def stamp():
    return {"boot": boot_id(), "mono": time.monotonic()}


def age(success):
    if not isinstance(success, dict) or not success.get("boot") or success["boot"] != boot_id():
        return None
    mono = success.get("mono")
    if type(mono) not in (int, float) or not math.isfinite(mono):
        return None
    elapsed = time.monotonic() - mono
    return elapsed if elapsed >= 0 else None


def cache_dir():
    return Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "termux-status"


def empty():
    return {"version": 1, "providers": {}}


def valid_data(provider, data):
    """Reject corrupt records rather than enabling permission-gated collection."""
    if not isinstance(data, dict):
        return False
    keys = {"wifi": {"connected", "ssid", "rssi", "level", "frequency_mhz", "link_speed_mbps"},
            "cells": {"registered"}, "device": {"carrier", "roaming", "data_enabled", "data_state", "network_type"},
            "notifications": {"packages"}, "location": {"enabled", "mode"}, "volume": {"streams"}}
    if set(data) != keys[provider]:
        return False
    if provider == "volume":
        streams = data["streams"]
        return isinstance(streams, dict) and bool(streams) and all(
            name in STREAMS and isinstance(value, dict) and set(value) == {"volume", "max_volume"}
            and type(value["volume"]) is int and type(value["max_volume"]) is int
            and 0 <= value["volume"] <= value["max_volume"] <= 100000 and value["max_volume"] > 0
            for name, value in streams.items())
    if provider == "notifications":
        return isinstance(data["packages"], dict) and all(
            isinstance(k, str) and re.fullmatch(r"[A-Za-z0-9_.]+", k) and type(v) is int and v >= 0
            for k, v in data["packages"].items())
    if provider == "cells":
        return isinstance(data["registered"], list) and all(
            isinstance(c, dict) and set(c) == {"index", "level", "dbm", "type"}
            and c["index"] == i + 1 and (c["level"] is None or type(c["level"]) is int and 0 <= c["level"] <= 4)
            for i, c in enumerate(data["registered"]))
    if provider == "wifi":
        return (data["connected"] is None or type(data["connected"]) is bool) and (
            data["level"] is None or type(data["level"]) is int and 0 <= data["level"] <= 4)
    if provider == "location":
        return type(data["enabled"]) is bool and type(data["mode"]) is int and 0 <= data["mode"] <= 3
    return all(value is None or isinstance(value, (str, bool)) for value in data.values())


def load(module):
    path = cache_dir() / (module + ".json")
    try:
        if path.is_symlink() or path.stat().st_size > 2 * 1024 * 1024:
            return empty()
        data = json.loads(path.read_text())
        if data.get("version") != 1 or not isinstance(data.get("providers"), dict):
            return empty()
        for provider, record in data["providers"].items():
            if provider not in PROVIDERS[module] or not isinstance(record, dict):
                return empty()
            if type(record.get("enabled")) is not bool or not isinstance(record.get("error"), (str, type(None))):
                return empty()
            success = record.get("success")
            if success is not None:
                if not isinstance(success, dict) or not valid_data(provider, success.get("data")):
                    return empty()
                if not isinstance(success.get("boot"), (str, type(None))) or type(success.get("mono")) not in (int, float):
                    return empty()
                if not math.isfinite(success["mono"]) or success["mono"] < 0:
                    return empty()
            elif record["enabled"]:
                return empty()
        return data
    except (OSError, ValueError, AttributeError, TypeError, RecursionError):
        return empty()


def prepare():
    directory = cache_dir()
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    if directory.is_symlink() or not directory.is_dir():
        raise OSError("refusing non-directory status cache")
    directory.chmod(0o700)
    return directory


def save(module, data):
    directory = prepare()
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", dir=directory, prefix=".status-", delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(data, stream, ensure_ascii=True, allow_nan=False)
        os.replace(temporary, directory / (module + ".json"))
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def acquire(module):
    fd = os.open(prepare() / (module + ".lock"), os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise OSError("refusing non-regular status lock")
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return fd
    except BlockingIOError:
        os.close(fd)
        return None
    except BaseException:
        os.close(fd)
        raise


def due(module, data):
    result = []
    for provider in PROVIDERS[module]:
        record = data["providers"].get(provider, {})
        enabled = record.get("enabled", provider not in GATED)
        elapsed = age(record.get("success"))
        if enabled and (elapsed is None or elapsed >= TTL[module]):
            result.append(provider)
    return result


def refresh(module, explicit=False):
    """Caller holds the module lock. Two cell providers run concurrently."""
    from concurrent.futures import ThreadPoolExecutor

    data = load(module)
    selected = PROVIDERS[module] if explicit else due(module, data)
    if not selected:
        return []
    for provider in selected:
        record = data["providers"].setdefault(provider, {})
        # A killed worker must not leave permission requests enabled indefinitely.
        record.update(enabled=False, error="refresh pending; retry --refresh if no result appears")
    save(module, data)
    errors = []

    def sample(provider):
        normalized = collect(provider)
        return {**stamp(), "data": normalized}

    with ThreadPoolExecutor(max_workers=len(selected)) as executor:
        futures = {provider: executor.submit(sample, provider) for provider in selected}
        for provider, future in futures.items():
            record = data["providers"][provider]
            try:
                success = future.result()
                record.update(enabled=True, error=None, success=success)
            except (ProviderError, OSError):
                # Never persist raw API errors, which can contain private data.
                error = future.exception()
                message = str(error) if isinstance(error, ProviderError) else "provider unavailable"
                record.update(enabled=False, error=message)
                errors.append(provider + ": " + message)
    save(module, data)
    return errors


def request(module, explicit=False):
    if not explicit and not due(module, load(module)):
        return []
    fd = acquire(module)
    if fd is None:
        return ["refresh already in progress"] if explicit else []
    try:
        if explicit:
            return refresh(module, explicit=True)
        if not due(module, load(module)):
            return []
        worker = Path(__file__).with_name("worker.py")
        subprocess.Popen([sys.executable, "-B", str(worker), module, str(fd)], pass_fds=(fd,),
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=True)
        return []
    finally:
        # No LOCK_UN: the inherited open-file description keeps the worker locked.
        os.close(fd)
