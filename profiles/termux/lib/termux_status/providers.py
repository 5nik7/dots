"""Reduce Android responses before they reach persistent state or diagnostics."""

import json
import os
import re
import selectors
import signal
import subprocess
import time
import unicodedata


TTL = {"wifi": 10, "cell": 15, "notification": 15, "location": 30, "volume": 5}
STREAMS = ("music", "ring", "notification", "alarm", "system", "call")
PROVIDERS = {"wifi": ("wifi",), "cell": ("cells", "device"),
             "notification": ("notifications",), "location": ("location",), "volume": ("volume",)}
GATED = {"cells", "device", "notifications"}
TIMEOUT = 4.0
MAX_BYTES = 2 * 1024 * 1024


class ProviderError(Exception):
    """A fixed, safe diagnostic; never include provider output."""


def clean(value):
    if not isinstance(value, str):
        return None
    return "".join(c for c in value[:256] if not unicodedata.category(c).startswith("C"))


def integer(value, low, high):
    return value if type(value) is int and low <= value <= high else None


def boolean(value):
    if type(value) is bool:
        return value
    if isinstance(value, str) and value.lower() in ("true", "false"):
        return value.lower() == "true"
    return None


def wifi(raw):
    # Older Android builds can represent an absent WifiInfo this way.
    if isinstance(raw, dict) and raw.get("API_ERROR") == "No current connection":
        raw = {"supplicant_state": "DISCONNECTED"}
    if not isinstance(raw, dict) or "supplicant_state" not in raw:
        raise ProviderError("invalid Wi-Fi response")
    state = raw["supplicant_state"]
    if state == "COMPLETED":
        connected = True
    elif state in ("DISCONNECTED", "INACTIVE", "INTERFACE_DISABLED", "UNINITIALIZED",
                   "SCANNING", "ASSOCIATING", "ASSOCIATED", "AUTHENTICATING",
                   "FOUR_WAY_HANDSHAKE", "GROUP_HANDSHAKE", "DORMANT"):
        connected = False
    else:
        connected = None
    rssi = integer(raw.get("rssi"), -126, -1) if connected else None
    level = sum(rssi >= threshold for threshold in (-85, -75, -67, -55)) if rssi is not None else None
    return {"connected": connected, "ssid": clean(raw.get("ssid")) if connected else None,
            "rssi": rssi, "level": level,
            "frequency_mhz": integer(raw.get("frequency_mhz"), 1, 100000) if connected else None,
            "link_speed_mbps": integer(raw.get("link_speed_mbps"), 0, 100000) if connected else None}


def cells(raw):
    if not isinstance(raw, list) or any(not isinstance(cell, dict) for cell in raw):
        raise ProviderError("invalid cellular response")
    registered = []
    for cell in raw:
        if boolean(cell.get("registered")) is True:
            registered.append({"index": len(registered) + 1,
                               "level": integer(cell.get("level"), 0, 4),
                               "dbm": integer(cell.get("dbm"), -200, -1),
                               "type": clean(cell.get("type"))})
    return {"registered": registered}


def device(raw):
    if not isinstance(raw, dict) or not any(k in raw for k in
                                          ("data_state", "network_operator_name", "network_type")):
        raise ProviderError("invalid telephony device response")
    return {"carrier": clean(raw.get("network_operator_name")),
            "roaming": boolean(raw.get("network_roaming")),
            "data_enabled": boolean(raw.get("data_enabled")),
            "data_state": clean(raw.get("data_state")),
            "network_type": clean(raw.get("network_type"))}


def notifications(raw):
    if not isinstance(raw, list):
        raise ProviderError("invalid notification response")
    packages = {}
    for entry in raw:
        if not isinstance(entry, dict):
            raise ProviderError("invalid notification entry")
        package = entry.get("packageName")
        if not isinstance(package, str) or not re.fullmatch(r"[A-Za-z0-9_.]+", package):
            raise ProviderError("invalid notification package")
        packages[package] = packages.get(package, 0) + 1
    return {"packages": packages}


def location(raw):
    mode = raw.strip()
    if mode not in ("0", "1", "2", "3"):
        raise ProviderError("location toggle unavailable")
    return {"enabled": mode != "0", "mode": int(mode)}


def volume(raw):
    if not isinstance(raw, list) or not raw:
        raise ProviderError("invalid volume response")
    streams = {}
    for entry in raw:
        if not isinstance(entry, dict):
            raise ProviderError("invalid volume stream")
        name = entry.get("stream")
        if not isinstance(name, str) or name not in STREAMS or name in streams:
            raise ProviderError("invalid volume stream")
        maximum = integer(entry.get("max_volume"), 1, 100000)
        value = integer(entry.get("volume"), 0, maximum or 0)
        if maximum is None or value is None:
            raise ProviderError("invalid volume level")
        streams[name] = {"volume": value, "max_volume": maximum}
    return {"streams": streams}


ADAPTERS = {"wifi": wifi, "cells": cells, "device": device,
            "notifications": notifications, "location": location, "volume": volume}


def command(provider):
    if provider == "location":
        return ["/system/bin/settings", "--user", str(os.getuid() // 100000),
                "get", "secure", "location_mode"]
    return [{"wifi": "termux-wifi-connectioninfo", "cells": "termux-telephony-cellinfo",
             "device": "termux-telephony-deviceinfo", "notifications": "termux-notification-list",
             "volume": "termux-volume"}[provider]]


def run_command(argv, timeout=TIMEOUT):
    """Bound time/output and kill the private child group, including descendants."""
    try:
        process = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                   stderr=subprocess.DEVNULL, start_new_session=True)
    except OSError:
        raise ProviderError("command unavailable") from None
    chunks, size = [], 0
    deadline = time.monotonic() + timeout
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise ProviderError("request timed out; check Android permissions and retry --refresh")
                if not selector.select(remaining):
                    continue
                chunk = os.read(process.stdout.fileno(), 65536)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_BYTES:
                    raise ProviderError("response exceeds size limit")
                chunks.append(chunk)
        try:
            status = process.wait(timeout=max(0.001, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            raise ProviderError("request timed out; retry --refresh") from None
        if status:
            raise ProviderError("request failed; check Android permissions and retry --refresh")
        return b"".join(chunks).decode("utf-8")
    except UnicodeError:
        raise ProviderError("invalid response encoding") from None
    finally:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()
        process.stdout.close()


def collect(provider):
    raw = run_command(command(provider))
    if provider != "location":
        try:
            raw = json.loads(raw)
        except (ValueError, RecursionError):
            raise ProviderError("invalid JSON response") from None
        if isinstance(raw, dict) and "error" in raw:
            raise ProviderError("API error; check Android permissions and retry --refresh")
    return ADAPTERS[provider](raw)
