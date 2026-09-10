"""Fixed-layout experimental bundles; caller owns every mutation destination."""

import gzip
import hashlib
import io
import json
import os
import stat
import tarfile
import zipfile

MAX_ARCHIVE = 16 * 1024 * 1024
MAX_TAR = 10 * 1024 * 1024
MAX_BINARY = 8 * 1024 * 1024


class ChecksumMismatch(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def json_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def payloads(binary, logo, identity, commit, source_hashes):
    platform, goos, architecture = identity
    name = "bin/dots-spike" + (".exe" if goos == "windows" else "")
    files = {name: binary, "logo.txt": logo}
    metadata = {"schema_version": 1, "platform": platform, "os": goos,
                "architecture": architecture, "source_commit": commit,
                "build_source_sha256": source_hashes,
                "files": {path: {"sha256": sha256(data), "bytes": len(data),
                                  "mode": "0755" if path == name else "0644"}
                          for path, data in files.items()}}
    files["bundle.json"] = json_bytes(metadata)
    return files, metadata


def pack(output, files, metadata):
    output.mkdir(mode=0o700)
    windows = metadata["os"] == "windows"
    name = f"dots-spike-{metadata['platform']}-{metadata['architecture']}"
    archive = output / (name + (".zip" if windows else ".tar.gz"))
    if windows:
        with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED) as bundle:
            for name, data in files.items():
                entry = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                entry.create_system = 3
                entry.external_attr = (stat.S_IFREG | (0o755 if name.startswith("bin/") else 0o644)) << 16
                entry.compress_type = zipfile.ZIP_DEFLATED
                bundle.writestr(entry, data)
    else:
        with archive.open("xb") as raw, gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w", format=tarfile.USTAR_FORMAT) as bundle:
                for name, data in files.items():
                    entry = tarfile.TarInfo(name)
                    entry.size = len(data)
                    entry.mode = 0o755 if name.startswith("bin/") else 0o644
                    bundle.addfile(entry, io.BytesIO(data))
    checksum = output / "SHA256SUMS"
    checksum.write_bytes(f"{sha256(archive.read_bytes())}  {archive.name}\n".encode("ascii"))
    return archive, checksum


def read_members(data, windows, expected):
    """Read bounded regular payloads; never use extract/extractall."""
    result = {}
    executable = "bin/dots-spike" + (".exe" if windows else "")
    limits = {executable: MAX_BINARY, "logo.txt": 65536, "bundle.json": 65536}

    def member(name, size, mode, regular, read):
        require(name in limits and name not in result, "Unexpected or duplicate archive path")
        require(regular, "Archive member is not a plain regular file")
        require(mode == (0o755 if name == executable else 0o644), "Unexpected archive permissions")
        require(0 <= size <= limits[name], "Archive member exceeds size limit")
        content = read()
        require(len(content) == size, "Archive member size differs")
        result[name] = content

    try:
        if windows:
            with zipfile.ZipFile(io.BytesIO(data)) as bundle:
                require(len(bundle.infolist()) == 3, "Expected exactly three archive members")
                for entry in bundle.infolist():
                    mode = entry.external_attr >> 16
                    require(not entry.flag_bits & 1 and entry.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED),
                            "Unsupported ZIP encoding")
                    member(entry.filename, entry.file_size, stat.S_IMODE(mode),
                           entry.create_system == 3 and stat.S_ISREG(mode), lambda: bundle.read(entry))
        else:
            with gzip.GzipFile(fileobj=io.BytesIO(data)) as compressed:
                raw = compressed.read(MAX_TAR + 1)
            require(len(raw) <= MAX_TAR, "Expanded archive exceeds size limit")
            with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as bundle:
                for entry in bundle:
                    member(entry.name, entry.size, entry.mode,
                           entry.type == tarfile.REGTYPE and not entry.pax_headers and not entry.issparse(),
                           lambda: bundle.extractfile(entry).read())
    except (tarfile.TarError, zipfile.BadZipFile, EOFError, OSError) as error:
        raise RuntimeError("Invalid archive encoding") from error
    require(set(result) == set(limits), "Archive layout is incomplete")
    require(result["bundle.json"] == json_bytes(expected), "Bundle metadata differs from expected build identity")
    for name, details in expected["files"].items():
        require(len(result[name]) == details["bytes"] and sha256(result[name]) == details["sha256"],
                "Bundle payload differs from expected build identity")
    return result


def verified_payloads(archive, checksum, expected):
    with checksum.open("rb") as stream:
        manifest = stream.read(513)
    with archive.open("rb") as stream:
        data = stream.read(MAX_ARCHIVE + 1)
    require(len(data) <= MAX_ARCHIVE, "Archive exceeds size limit")
    # Verify and parse the same in-memory bytes, avoiding path replacement between reads.
    wanted = f"{sha256(data)}  {archive.name}\n".encode("ascii")
    if manifest != wanted:
        raise ChecksumMismatch("Archive SHA-256 checksum mismatch; extraction refused")
    return read_members(data, expected["os"] == "windows", expected)


def extract_verified(archive, checksum, destination, expected):
    files = verified_payloads(archive, checksum, expected)
    # This API is private to test-owned roots. No existing destination is reused.
    destination.mkdir(mode=0o700)
    (destination / "bin").mkdir(mode=0o755)
    for name, data in files.items():
        path = destination / name
        with path.open("xb") as stream:
            stream.write(data)
        if os.name != "nt":
            path.chmod(0o755 if name.startswith("bin/") else 0o644)
    return destination / ("bin/dots-spike.exe" if expected["os"] == "windows" else "bin/dots-spike")
