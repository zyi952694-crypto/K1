#!/usr/bin/env python3
"""Validate K1 Markdown navigation, assets, anchors, metadata, and migration coverage."""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path
from urllib.parse import unquote, urlsplit

from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parents[1]
PARSER = MarkdownIt('commonmark', {'html': True}).enable('table')
FRONTMATTER = re.compile(r'^---\n(.*?)\n---\n', re.S)


def heading_slug(text: str) -> str:
    text = re.sub(r'<[^>]*>', '', text).lower()
    return ''.join(
        '-' if c == ' ' else c
        for c in text
        if c in ' -_' or unicodedata.category(c)[0] in ('L', 'N')
    )


def walk(tokens):
    for token in tokens:
        yield token
        if token.children:
            yield from walk(token.children)


def inspect(path: Path):
    text = path.read_text(encoding='utf-8')
    front = FRONTMATTER.match(text)
    tokens = PARSER.parse(FRONTMATTER.sub('', text))
    anchors, counts, levels, links, failures = set(), Counter(), [], [], []
    for number, line in enumerate(text.splitlines(), 1):
        if line != line.rstrip():
            failures.append(f'line {number}: trailing whitespace')
    if not text.endswith('\n'):
        failures.append('missing final newline')
    for i, token in enumerate(tokens):
        if token.type == 'heading_open':
            levels.append(int(token.tag[1]))
            inline = tokens[i + 1]
            content = ''.join(t.content for t in inline.children or []
                              if t.type in ('text', 'code_inline', 'image'))
            anchor = heading_slug(content)
            suffix = f'-{counts[anchor]}' if counts[anchor] else ''
            anchors.add(anchor + suffix)
            counts[anchor] += 1
        if token.type == 'fence':
            if not token.info:
                failures.append(f'line {token.map[0] + 1}: code fence has no language')
            lines = FRONTMATTER.sub('', text).splitlines()
            if not re.match(r'^\s*' + re.escape(token.markup[0]) +
                            '{' + str(len(token.markup)) + r',}\s*$',
                            lines[token.map[1] - 1]):
                failures.append(f'line {token.map[0] + 1}: unclosed code fence')
    if levels.count(1) != 1:
        failures.append(f'expected one H1, got {levels.count(1)}')
    for previous, current in zip(levels, levels[1:]):
        if current > previous + 1:
            failures.append(f'heading jump H{previous} -> H{current}')
    for token in walk(tokens):
        if token.type == 'link_open':
            links.append(token.attrGet('href'))
        elif token.type == 'image':
            links.append(token.attrGet('src'))
        elif token.type in ('html_block', 'html_inline'):
            links.extend(re.findall(r'(?:href|src)=[\"\x27]([^\"\x27]+)', token.content))
            anchors.update(re.findall(r'(?:id|name)=[\"\x27]([^\"\x27]+)', token.content))
    return front, anchors, links, failures


def main() -> int:
    files = sorted(p for p in ROOT.rglob('*.md')
                   if not any(part.startswith('.') for part in p.relative_to(ROOT).parts))
    info = {p: inspect(p) for p in files}
    errors, slugs, graph = [], {}, {}
    link_count = 0
    for path, (front, anchors, links, failures) in info.items():
        rel = path.relative_to(ROOT).as_posix()
        errors.extend(f'{rel}: {failure}' for failure in failures)
        if rel != 'README.md' and not rel.startswith('docs/'):
            if not front:
                errors.append(f'{rel}: missing frontmatter')
            else:
                slug = re.search(r'^slug: (.+)$', front.group(1), re.M)
                position = re.search(r'^sidebar_position: \d+$', front.group(1), re.M)
                if not slug or not slug.group(1).startswith('/k1') or not position:
                    errors.append(f'{rel}: invalid sidebar_position or K1 slug')
                elif slug.group(1) in slugs:
                    errors.append(f'{rel}: duplicate slug with {slugs[slug.group(1)]}')
                else:
                    slugs[slug.group(1)] = rel
        graph[path] = set()
        for url in links:
            if not url or urlsplit(url).scheme or url.startswith('//'):
                continue
            link_count += 1
            url_path, _, anchor = url.partition('#')
            target = (path.parent / unquote(url_path.split('?')[0])).resolve() if url_path else path
            if not target.is_relative_to(ROOT) or not target.exists():
                errors.append(f'{rel}: missing local target {url}')
                continue
            if target in info:
                graph[path].add(target)
                if anchor and unquote(anchor) not in info[target][1]:
                    errors.append(f'{rel}: missing heading anchor {url}')
    manifest = json.loads((ROOT / 'docs/migration-map.json').read_text())
    sources = set()
    for row in manifest['pages']:
        source = (row['source_repository'], row['source'])
        if source in sources:
            errors.append(f'duplicate migration source: {source}')
        sources.add(source)
        if not (ROOT / row['target']).is_file():
            errors.append(f'missing migrated page: {row["target"]}')
    for rel in manifest['k3_framework']:
        if not (ROOT / rel).is_file():
            errors.append(f'missing K3 chapter 4/5 framework page: {rel}')
    for rel in manifest['pending_pages']:
        if 'K1 兼容性待确认' not in (ROOT / rel).read_text():
            errors.append(f'unmarked compatibility placeholder: {rel}')
    visited, pending = set(), [ROOT / 'README.md', ROOT / 'index.md']
    while pending:
        path = pending.pop()
        if path in visited:
            continue
        visited.add(path)
        pending.extend(graph.get(path, set()) - visited)
    for path in files:
        if path not in visited:
            errors.append(f'unreachable Markdown page: {path.relative_to(ROOT)}')
    if errors:
        print('\n'.join('FAIL: ' + error for error in errors))
        return 1
    print(f'PASS: {len(files)} Markdown pages; {link_count} local links/assets/anchors; '
          f'{len(sources)} migration records; {len(manifest["k3_framework"])} K3 framework paths; '
          f'{len(manifest["pending_pages"])} explicit compatibility placeholders.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
