"""Pure foreground gradients for trusted, already sanitized single-cell artwork."""
import re


def endpoints(colors):
    if not isinstance(colors, dict):
        return None
    values = [colors.get(name) for name in ('hint', 'info', 'accent')]
    if not all(isinstance(value, str) and re.fullmatch(r'#[0-9a-fA-F]{6}', value) for value in values):
        return None
    return tuple(tuple(int(value[i:i + 2], 16) for i in (1, 3, 5)) for value in values)


def gradient(lines, colors, *, regions=(), restore='\x1b[39m'):
    """Each (left, top, right, bottom) region receives its own full diagonal.

    Blank cells keep their bytes but do not set gradient bounds. Integer scores
    give horizontal/upward positions equal weight; normalize over visible cells
    so the extreme cells get hint/accent and the midpoint gets info. Interpolate
    each half separately, rounding RGB halves upward like the builtin Bash path.
    """
    stops = endpoints(colors)
    if stops is None:
        return list(lines)
    start, middle, end = stops
    regions = regions or ((0, 0, max(map(len, lines), default=0), len(lines)),)
    codes = {}
    for left, top, right, bottom in regions:
        points = [(x, y) for y in range(top, min(bottom, len(lines)))
                  for x in range(left, min(right, len(lines[y]))) if lines[y][x] not in (' ', '\u2800')]
        if not points:
            continue
        xmin, xmax = min(x for x, _ in points), max(x for x, _ in points)
        ymin, ymax = min(y for _, y in points), max(y for _, y in points)
        scores = {(x, y): (x - xmin) * max(1, ymax - ymin) + (ymax - y) * max(1, xmax - xmin)
                  for x, y in points}
        low, high = min(scores.values()), max(scores.values())
        span = max(1, high - low)
        for point, score in scores.items():
            step = 2 * (score - low)
            first, last = (start, middle) if step <= span else (middle, end)
            if step > span:
                step -= span
            rgb = [(a * (span - step) + b * step + span // 2) // span for a, b in zip(first, last)]
            codes[point] = '\x1b[38;2;%d;%d;%dm' % tuple(rgb)
    result = []
    for y, line in enumerate(lines):
        parts, previous = [], ''
        for x, char in enumerate(line):
            code = codes.get((x, y))
            if code and code != previous:
                parts.append(code)
                previous = code
            parts.append(char)
        result.append(''.join(parts) + (restore if previous else ''))
    return result
