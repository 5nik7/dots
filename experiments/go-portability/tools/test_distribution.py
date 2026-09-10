"""Distribution failure regressions; all archives and destinations are owned."""

import io
import os
from pathlib import Path
import stat
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import distribution as dist


class DistributionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="dots-distribution-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()

    def fixture(self, windows):
        identity = ("windows", "windows", "amd64") if windows else ("termux", "android", "arm64")
        return dist.payloads(b"fixture executable", b"PUBLIC LOGO\n", identity, "a" * 40, {"go.mod": "b" * 64})

    def archive(self, windows, entries):
        path = self.root / ("fixture.zip" if windows else "fixture.tar.gz")
        if windows:
            with zipfile.ZipFile(path, "w") as bundle:
                for name, data, mode, kind in entries:
                    entry = zipfile.ZipInfo(name)
                    entry.create_system = 3
                    entry.external_attr = ((stat.S_IFREG if kind == "file" else stat.S_IFLNK) | mode) << 16
                    bundle.writestr(entry, data)
        else:
            with tarfile.open(path, "w:gz") as bundle:
                for name, data, mode, kind in entries:
                    entry = tarfile.TarInfo(name)
                    entry.mode = mode
                    entry.type = {"file": tarfile.REGTYPE, "link": tarfile.SYMTYPE,
                                  "hardlink": tarfile.LNKTYPE, "fifo": tarfile.FIFOTYPE,
                                  "directory": tarfile.DIRTYPE}[kind]
                    entry.linkname = "../owned sentinel"
                    entry.size = len(data) if kind == "file" else 0
                    bundle.addfile(entry, io.BytesIO(data) if kind == "file" else None)
        checksum = self.root / "SHA256SUMS"
        checksum.write_bytes(f"{dist.sha256(path.read_bytes())}  {path.name}\n".encode("ascii"))
        return path, checksum

    def entries(self, files):
        return [(name, data, 0o755 if name.startswith("bin/") else 0o644, "file") for name, data in files.items()]

    def rejected(self, windows, entries, expected, reason):
        archive, checksum = self.archive(windows, entries)
        destination = self.root / "new directory 日本語"
        with self.assertRaisesRegex(RuntimeError, reason):
            dist.extract_verified(archive, checksum, destination, expected)
        self.assertFalse(destination.exists(), "Rejected input created an extraction root")

    def test_round_trip_both_formats(self):
        for windows in (False, True):
            with self.subTest(windows=windows):
                files, metadata = self.fixture(windows)
                archive, checksum = dist.pack(self.root / str(windows), files, metadata)
                destination = self.root / ("extracted 日本語 " + str(windows))
                binary = dist.extract_verified(archive, checksum, destination, metadata)
                self.assertEqual(binary.read_bytes(), files[next(iter(files))])
                self.assertEqual({p.relative_to(destination).as_posix() for p in destination.rglob('*') if p.is_file()}, set(files))
                if os.name != "nt":
                    self.assertEqual(stat.S_IMODE(binary.stat().st_mode), 0o755)
                    self.assertEqual(stat.S_IMODE((destination / "logo.txt").stat().st_mode), 0o644)

    def test_checksum_rejected_before_parsing_or_extraction(self):
        for windows in (False, True):
            files, metadata = self.fixture(windows)
            archive, checksum = self.archive(windows, self.entries(files))
            original = archive.read_bytes()
            archive.write_bytes(original[:-1] + bytes([original[-1] ^ 1]))
            with patch.object(dist, "read_members") as parser:
                with self.assertRaisesRegex(dist.ChecksumMismatch, "checksum mismatch"):
                    dist.extract_verified(archive, checksum, self.root / "never created", metadata)
                parser.assert_not_called()
            self.assertFalse((self.root / "never created").exists())
            archive.write_bytes(original)
            checksum.write_text("invalid manifest\n")
            with self.assertRaises(dist.ChecksumMismatch):
                dist.extract_verified(archive, checksum, self.root / "never created", metadata)

    def test_invalid_paths_and_duplicates(self):
        sentinel = self.root / "owned sentinel"
        sentinel.write_bytes(b"keep")
        for windows in (False, True):
            files, metadata = self.fixture(windows)
            for name in ("../owned sentinel", "/absolute", "C:/escape", "bin\\escape", "bin/../escape",
                         "bin/dots-spike:stream", "bin/CON", "logo.txt.", "LOGO.TXT", "logo.txt"):
                with self.subTest(windows=windows, name=name):
                    entries = self.entries(files)
                    entries[0] = (name, *entries[0][1:])
                    if name == "logo.txt":
                        entries[0] = (name, entries[0][1], 0o644, "file")
                    self.rejected(windows, entries, metadata, "path")
                    self.assertEqual(sentinel.read_bytes(), b"keep")

    def test_nonregular_members_and_modes(self):
        for windows in (False, True):
            files, metadata = self.fixture(windows)
            for kind in (("link",) if windows else ("link", "hardlink", "fifo", "directory")):
                with self.subTest(windows=windows, kind=kind):
                    entries = self.entries(files)
                    entries[0] = (*entries[0][:3], kind)
                    self.rejected(windows, entries, metadata, "regular file")
            for mode in (0o644, 0o777, 0o4755):
                entries = self.entries(files)
                entries[0] = (*entries[0][:2], mode, "file")
                self.rejected(windows, entries, metadata, "permissions")

    def test_missing_members_and_payload_identity(self):
        for windows in (False, True):
            files, metadata = self.fixture(windows)
            entries = self.entries(files)
            self.rejected(windows, entries[:-1], metadata, "members|incomplete")
            changed = list(entries)
            changed[0] = (changed[0][0], b"wrong executable", *changed[0][2:])
            self.rejected(windows, changed, metadata, "payload")
            changed = list(entries)
            changed[-1] = ("bundle.json", dist.json_bytes(dict(metadata, source_commit="c" * 40)), 0o644, "file")
            self.rejected(windows, changed, metadata, "metadata")

    def test_limits_and_invalid_archive(self):
        for windows in (False, True):
            files, metadata = self.fixture(windows)
            archive, checksum = self.archive(windows, self.entries(files))
            with patch.object(dist, "MAX_ARCHIVE", 1):
                with self.assertRaisesRegex(RuntimeError, "size limit"):
                    dist.extract_verified(archive, checksum, self.root / "never created", metadata)
            with patch.object(dist, "MAX_BINARY", 1):
                with self.assertRaisesRegex(RuntimeError, "size limit"):
                    dist.extract_verified(archive, checksum, self.root / "never created", metadata)
            if not windows:
                with patch.object(dist, "MAX_TAR", 1):
                    with self.assertRaisesRegex(RuntimeError, "size limit"):
                        dist.extract_verified(archive, checksum, self.root / "never created", metadata)
            archive.write_bytes(b"invalid archive")
            checksum.write_bytes(f"{dist.sha256(archive.read_bytes())}  {archive.name}\n".encode())
            with self.assertRaisesRegex(RuntimeError, "Invalid archive"):
                dist.extract_verified(archive, checksum, self.root / "never created", metadata)
            self.assertFalse((self.root / "never created").exists())

    def test_existing_destination_preserved(self):
        destination = self.root / "existing"
        destination.mkdir()
        sentinel = destination / "keep"
        sentinel.write_bytes(b"keep")
        for windows in (False, True):
            files, metadata = self.fixture(windows)
            archive, checksum = self.archive(windows, self.entries(files))
            with self.assertRaises(FileExistsError):
                dist.extract_verified(archive, checksum, destination, metadata)
            self.assertEqual(list(destination.iterdir()), [sentinel])
            self.assertEqual(sentinel.read_bytes(), b"keep")


if __name__ == "__main__":
    unittest.main(verbosity=2)
