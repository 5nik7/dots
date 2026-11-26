"""Read the OpenType tables used by the personal font inventory."""
import re
import struct


def _tables(data):
    if len(data) < 12 or data[:4] not in (b'\x00\x01\x00\x00', b'true', b'OTTO'):
        raise ValueError('expected a standalone TrueType or OpenType font')
    count, = struct.unpack_from('>H', data, 4)
    directory_end = 12 + count * 16
    if directory_end > len(data):
        raise ValueError('truncated table directory')
    tables = {}
    ranges = []
    for tag, _, offset, length in struct.iter_unpack('>4sIII', data[12:directory_end]):
        end = offset + length
        if tag in tables or offset < directory_end or end > len(data):
            raise ValueError('invalid table directory')
        tables[tag] = data[offset:end]
        if length:
            ranges.append((offset, end))
    previous_end = directory_end
    for offset, end in sorted(ranges):
        if offset < previous_end:
            raise ValueError('overlapping font tables')
        previous_end = end
    return tables


_MAC_ENCODINGS = {
    1: 'shift_jis', 2: 'big5', 3: 'euc_kr', 6: 'mac_greek', 7: 'mac_cyrillic',
    25: 'gb2312', 29: 'mac_latin2', 35: 'mac_turkish', 37: 'mac_iceland',
}
_MAC_ROMAN_LANGUAGES = {
    15: 'mac_iceland', 17: 'mac_turkish', 18: 'mac_croatian', 37: 'mac_romanian',
    **dict.fromkeys((24, 25, 26, 27, 28, 36, 38, 39, 40), 'mac_latin2'),
}
_WINDOWS_ENCODINGS = {
    0: 'utf-16-be', 1: 'utf-16-be', 2: 'shift_jis', 3: 'gb2312', 4: 'big5',
    5: 'euc_kr', 6: 'johab', 10: 'utf-16-be',
}
# Mac East Asian encodings add single-byte characters to the base codecs.
# Keys are the surrogateescape values for bytes rejected by those codecs.
_MAC_SYMBOLS = {0xDCA0: '\u00a0', 0xDCFD: '©', 0xDCFE: '™', 0xDCFF: '…'}
_MAC_EXTENSIONS = {
    'shift_jis': {**_MAC_SYMBOLS, 0xDC80: '\\', 0xDCFC: '|'},
    'big5': {**_MAC_SYMBOLS, 0xDC80: '\\'},
    'euc_kr': {0xDC80: '\u00a0', 0xDC81: '₩', 0xDC82: '—', 0xDC83: '©',
               0xDCFE: '™', 0xDCFF: '…'},
    'gb2312': {**_MAC_SYMBOLS, 0xDC80: 'ü'},
}


def _encoding(platform, encoding, language):
    if platform == 0 and encoding <= 6:
        return 'utf-16-be'
    if platform == 1:
        if encoding == 0:
            return _MAC_ROMAN_LANGUAGES.get(language, 'mac_roman')
        return _MAC_ENCODINGS.get(encoding, 'ascii')
    if platform == 2:
        return {1: 'utf-16-be', 2: 'latin-1'}.get(encoding, 'ascii')
    if platform == 3:
        return _WINDOWS_ENCODINGS.get(encoding, 'ascii')
    return 'ascii'


def _names(tables, *, prefer_win32=False):
    if b'name' not in tables:
        raise ValueError('missing name table')
    table = tables[b'name']
    if len(table) < 6:
        raise ValueError('truncated name table')
    version, count, storage = struct.unpack_from('>HHH', table)
    records_end = 6 + 12 * count
    if version not in (0, 1) or not records_end <= storage <= len(table):
        raise ValueError('invalid name table')
    if version == 1:
        if records_end + 2 > storage:
            raise ValueError('truncated name language tags')
        language_count, = struct.unpack_from('>H', table, records_end)
        language_end = records_end + 2 + 4 * language_count
        if language_end > storage:
            raise ValueError('truncated name language tags')
        for length, offset in struct.iter_unpack('>HH', table[records_end + 2:language_end]):
            if storage + offset + length > len(table):
                raise ValueError('invalid name language tag')

    # Only decode records needed by Dots. For each ID, prefer the first
    # Windows US English record, then the first Mac English, then the last
    # other decodable record, matching the previous inventory's selection.
    candidates = []
    for index, record in enumerate(struct.iter_unpack('>6H', table[6:records_end])):
        platform, encoding, language, name_id, length, offset = record
        start = storage + offset
        if start + length > len(table):
            raise ValueError('invalid name string offset')
        if name_id not in (1, 2, 4, 5, 16, 17, 21, 22) or not length:
            continue
        priority = 2
        if platform == 3 and language == 0x409:
            priority = 0
            if prefer_win32 and name_id == 1 and encoding in (1, 10):
                # GDI prefers US English Unicode BMP, then full Unicode.
                priority = -2 if encoding == 1 else -1
        elif platform == 1 and language == 0:
            priority = 1
        order = -index if priority == 2 else index
        candidates.append((priority, order, name_id, start, length, platform, _encoding(platform, encoding, language)))

    names = {}
    # Thousands of overlapping records can point at the same undecodable
    # strings. Eight successful 16-bit lengths consume at most 512 KiB.
    decode_budget = 4 * 1024 * 1024
    for _, _, name_id, start, length, platform, codec in sorted(candidates):
        if name_id in names:
            continue
        decode_budget -= length
        if decode_budget < 0:
            raise ValueError('too many undecodable font names')
        raw = bytes(table[start:start + length])
        try:
            if platform == 1 and codec in _MAC_EXTENSIONS:
                value = raw.decode(codec, 'surrogateescape').translate(_MAC_EXTENSIONS[codec])
                if any(0xDC80 <= ord(c) <= 0xDCFF for c in value):
                    continue
            else:
                value = raw.decode(codec)
        except UnicodeDecodeError:
            continue
        names[name_id] = value
    return names


def _axes(table):
    if len(table) < 16:
        raise ValueError('truncated variation header')
    major, minor, offset, _, count, stride, instances, instance_size = struct.unpack_from('>8H', table)
    axes_end = offset + count * stride
    if ((major, minor) != (1, 0) or offset < 16 or stride < 20 or
            (instances and instance_size < 4 + 4 * count) or
            axes_end + instances * instance_size > len(table)):
        raise ValueError('invalid variation table')
    axes = []
    seen = set()
    for start in range(offset, axes_end, stride):
        tag, minimum, default, maximum = struct.unpack_from('>4siii', table, start)
        if (not all(32 <= char <= 126 for char in tag) or tag in seen or
                not minimum <= default <= maximum):
            raise ValueError('invalid variation axis')
        seen.add(tag)
        axes.append(dict(tag=tag.decode('ascii'), minimum=minimum / 65536,
                         default=default / 65536, maximum=maximum / 65536))
    return axes


def _fixed_pitch(table):
    if len(table) < 32:
        raise ValueError('truncated post header')
    version, = struct.unpack_from('>I', table)
    if version not in (0x10000, 0x20000, 0x30000, 0x40000):
        raise ValueError('unsupported post table version')
    if version == 0x20000:
        if len(table) < 34 or 34 + 2 * struct.unpack_from('>H', table, 32)[0] > len(table):
            raise ValueError('truncated post glyph indices')
    if version == 0x40000 and len(table) % 2:
        raise ValueError('truncated post glyph index')
    return bool(struct.unpack_from('>I', table, 12)[0])


def _variant(family):
    for pattern, label in ((r'(Nerd Font Mono|NFM)\b', 'mono'),
                           (r'(Nerd Font Propo|NFP)\b', 'propo'),
                           (r'(Nerd Font|NF)\b', 'nerd')):
        if re.search(pattern, family):
            return label
    return 'original'


def windows_family_name(data):
    names = _names(_tables(memoryview(data)), prefer_win32=True)
    value = names.get(1) or names.get(21) or names.get(16)
    if not value or any(ord(c) < 32 for c in value):
        raise ValueError('font has no usable Windows family name')
    return value


def face_fields(data):
    """Return the face fields in storage order and its internal version string."""
    tables = _tables(memoryview(data))
    names = _names(tables)
    family = names.get(21) or names.get(16) or names.get(1)
    style = names.get(22) or names.get(17) or names.get(2) or 'Regular'
    full = names.get(4) or f'{family} {style}'
    if not family or any(ord(c) < 32 or 127 <= ord(c) < 160 for c in family + style + full):
        raise ValueError('invalid font names')
    mono = _fixed_pitch(tables[b'post']) if b'post' in tables else False
    axes = _axes(tables[b'fvar']) if b'fvar' in tables else []
    return dict(family=family, style=style, full_name=full, variant=_variant(family), monospace=mono,
                variable=bool(axes), axes=axes), names.get(5)
