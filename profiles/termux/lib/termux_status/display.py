"""Build the public snapshot and render icons without ANSI styling."""

import os

from .cache import MAX_AGE, age
from .providers import GATED, PROVIDERS, TTL


COMMON_FIELDS = ("module", "state", "icon", "text", "age_seconds", "stale", "error")
DATA_FIELDS = {
    "wifi": ("connected", "ssid", "rssi", "level", "frequency_mhz", "link_speed_mbps"),
    "cell": ("level", "dbm", "type", "index", "registered_count", "carrier", "roaming",
             "data_enabled", "data_state", "network_type", "device_age_seconds", "device_stale"),
    "notification": ("count", "package_count"),
    "location": ("enabled", "mode"),
    "volume": ("stream", "volume", "max_volume", "percent"),
}
ICONS = {
    "wifi": {"unknown": "\U000f092b", "off": "\U000f05aa",
             "levels": tuple(chr(c) for c in (0xF092F, 0xF091F, 0xF0922, 0xF0925, 0xF0928))},
    "cell": {"unknown": "\U000f08fe?", "off": "\U000f08fc",
             "levels": tuple(chr(c) for c in (0xF08FE, 0xF08F4, 0xF08F6, 0xF08F8, 0xF08FA))},
    "notification": {"unknown": "\U000f0e81", "off": "\U000f009c", "on": "\U000f009a"},
    "location": {"unknown": "\U000f0f08", "off": "\U000f0351", "on": "\U000f07d9"},
    "volume": {"unknown": "\U000f0e08", "muted": "\U000f075f", "low": "\U000f057f",
               "medium": "\U000f0580", "high": "\U000f057e"},
}


def snapshot(module, cache, args):
    values, ages, stale_providers, errors = {}, {}, [], []
    for provider in PROVIDERS[module]:
        record = cache["providers"].get(provider, {})
        elapsed = age(record.get("success"))
        if elapsed is not None and elapsed <= MAX_AGE:
            values[provider] = record["success"]["data"]
            ages[provider] = round(elapsed, 3)
            if elapsed >= TTL[module] or record.get("error"):
                stale_providers.append(provider)
        if record.get("error"):
            errors.append(provider + ": " + record["error"])
        elif provider not in values:
            reason = "run --refresh to enable" if provider in GATED and not record.get("enabled") else "no recent sample"
            errors.append(provider + ": " + reason)

    data = {field: None for field in DATA_FIELDS[module]}
    state, text, icon = "unknown", module + ":?", ICONS[module]["unknown"]
    primary = PROVIDERS[module][0]
    if module == "wifi" and "wifi" in values:
        data.update(values["wifi"])
        if data["connected"] is True:
            state = "connected"
            level = data["level"]
            text = "wifi:" + (str(level) + "/4" if level is not None else "?")
            if level is not None:
                icon = ICONS[module]["levels"][level]
        elif data["connected"] is False:
            state, text, icon = "disconnected", "wifi:off", ICONS[module]["off"]
    elif module == "cell":
        data["registered"] = values.get("cells", {}).get("registered")
        if "device" in values:
            data.update(values["device"])
            data.update(device_age_seconds=ages["device"], device_stale="device" in stale_providers)
        if "cells" in values:
            registered = values["cells"]["registered"]
            data["registered_count"] = len(registered)
            if args.cell is not None:
                selected = next((cell for cell in registered if cell["index"] == args.cell), None)
                if selected is None:
                    errors.append("selected registered cell unavailable")
            else:
                selected = max(registered, key=lambda c: c["level"] if c["level"] is not None else -1,
                               default=None)
            if selected:
                data.update(selected)
                state = "registered"
                level = selected["level"]
                text = "cell:" + (str(level) + "/4" if level is not None else "?")
                if level is not None:
                    icon = ICONS[module]["levels"][level]
            elif args.cell is None:
                state, text, icon = "unregistered", "cell:off", ICONS[module]["off"]
    elif module == "notification" and "notifications" in values:
        packages = values["notifications"]["packages"]
        excluded = set(args.exclude_package)
        if not args.include_self:
            excluded.update(("com.termux", "com.termux.api"))
            package = os.environ.get("TERMUX_APP__PACKAGE_NAME")
            if package:
                excluded.update((package, package + ".api"))
        included = set(args.include_package)
        packages = {name: count for name, count in packages.items()
                    if name not in excluded and (not included or name in included)}
        count = sum(packages.values())
        data.update(count=count, package_count=len(packages), packages=packages)
        state, text = ("active" if count else "inactive"), f"notifications:{count}"
        icon = ICONS[module]["on" if count else "off"]
    elif module == "volume":
        data["stream"] = args.stream
        selected = values.get("volume", {}).get("streams", {}).get(args.stream)
        if selected is not None:
            data.update(selected)
            data["percent"] = (data["volume"] * 100 + data["max_volume"] // 2) // data["max_volume"]
            percent = data["percent"]
            state = "muted" if data["volume"] == 0 else "low" if percent <= 33 else "medium" if percent <= 66 else "high"
            icon, text = ICONS[module][state], f"{args.stream}:{percent}%"
        elif "volume" in values:
            errors.append("selected volume stream unavailable")
    elif module == "location" and "location" in values:
        data.update(values["location"])
        enabled = data["enabled"]
        state, text = ("enabled", "location:on") if enabled else ("disabled", "location:off")
        icon = ICONS[module]["on" if enabled else "off"]
    stale = bool(stale_providers)
    if stale:
        icon += "~"
        text += "~"
    return {"module": module, "state": state, "icon": icon, "text": text,
            "age_seconds": ages.get(primary), "stale": stale,
            "error": "; ".join(errors) or None, "data": data}
