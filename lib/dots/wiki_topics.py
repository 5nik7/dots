"""Ephemeral topic records over canonical documentation; no persistent index."""
import re
import unicodedata
from urllib.parse import quote


def headings(text):
    counts, stack, rows = {}, [], []
    fence = None
    for index, line in enumerate(text.splitlines(keepends=True)):
        marker = re.match(r'^ {0,3}(`{3,}|~{3,})(.*)$', line)
        if marker:
            run, tail = marker.groups()
            if fence is None:
                fence = (run[0], len(run))
            elif run[0] == fence[0] and len(run) >= fence[1] and not tail.strip():
                fence = None
            continue
        if fence:
            continue
        match = re.match(r'^ {0,3}(#{1,6})\s+(.+?)\s*#*\s*$', line)
        if not match:
            continue
        level, title = len(match[1]), match[2]
        value = re.sub(r'<[^>]+>', '', title).lower()
        value = re.sub(r'\[([^]]+)\]\([^)]*\)', r'\1', value)
        slug = ''.join(c for c in value if c in '-_ ' or unicodedata.category(c)[0] in ('L', 'N', 'M')).replace(' ', '-')
        count = counts.get(slug, 0)
        counts[slug] = count + 1
        anchor = slug + ('-' + str(count) if count else '')
        plain = re.sub(r'\[([^]]+)\]\([^)]*\)', r'\1', re.sub(r'<[^>]+>', '', title))
        plain = plain.replace('`', '').replace('**', '')
        while stack and stack[-1][0] >= level:
            stack.pop()
        stack.append((level, plain))
        rows.append(dict(index=index, level=level, heading=plain, anchor=anchor,
                         breadcrumb=' / '.join(item[1] for item in stack)))
    return rows


def snapshot(root):
    from wiki import Reader, manifest
    from wiki_commands import markdown
    reader = Reader(root)
    spec = manifest(reader)
    pages, records = {}, []
    for page in spec['pages']:
        text = (reader.read(page['source']).decode() if page.get('source') else markdown(reader))
        pages[page['id']] = text
        lines = text.splitlines(keepends=True)
        rows = headings(text)
        # A page record covers its introduction, not every descendant's body.
        intro_end = next((h['index'] for h in rows if h['level'] > 1), len(lines))
        base = dict(page=page['id'], title=page['title'], section=page['section'])
        url = spec['web_url'].rstrip('/') + '/' + quote(page['id'], safe='-_')
        records.append(dict(base, heading='', breadcrumb=page['title'], anchor='', line=1,
                            url=url, content=''.join(lines[:intro_end])))
        for i, heading in enumerate(rows):
            if heading['level'] == 1:
                continue
            end = next((h['index'] for h in rows[i + 1:] if h['level'] <= heading['level']), len(lines))
            # Matching only a section's own text avoids parent/child duplicate hits.
            own_end = rows[i + 1]['index'] if i + 1 < len(rows) else len(lines)
            records.append(dict(base, **{k: heading[k] for k in ('heading', 'breadcrumb', 'anchor')},
                                line=heading['index'] + 1, url=url + '#' + quote(heading['anchor'], safe='-_'),
                                content=''.join(lines[heading['index']:end]),
                                match_content=''.join(lines[heading['index']:own_end])))
    return pages, records


def search(records, query):
    terms = query.casefold().split()
    if not terms:
        raise ValueError('topic query must contain text')
    phrase = ' '.join(terms)
    ranked = []
    for order, row in enumerate(records):
        title = row['title'].casefold()
        heading = row['breadcrumb'].casefold()
        body = row.get('match_content', row['content'])
        haystack = title + '\n' + heading + '\n' + body.casefold()
        if not all(term in haystack for term in terms):
            continue
        rank = (0 if phrase in title or phrase in heading else
                1 if all(term in title + ' ' + heading for term in terms) else 2)
        excerpt = next((line.strip() for line in body.splitlines()
                        if line.strip() and not line.lstrip().startswith(('#', '```', '~~~'))
                        and any(term in line.casefold() for term in terms)), row['heading'] or row['title'])
        item = {k: row[k] for k in ('page', 'title', 'section', 'heading', 'breadcrumb', 'anchor', 'line', 'url')}
        item['text'] = excerpt[:240] + ('…' if len(excerpt) > 240 else '')
        ranked.append((rank, order, item))
    return [item for _, _, item in sorted(ranked, key=lambda value: value[:2])]


def section_text(row):
    return '# ' + row['title'] + '\n\n' + row['breadcrumb'] + '\n\n' + row['content'].rstrip() + '\n'
