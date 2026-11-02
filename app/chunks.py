"""Deterministic character chunks with offsets into the original material."""

import re

_URL = re.compile(r'https?://\S+|[\w.+-]+@[\w-]+\.[\w.-]+')

CHUNK_SIZE = 800
CHUNK_OVERLAP = 80


def split_chunks(content, strategy="auto", max_chars=CHUNK_SIZE, overlap_chars=CHUNK_OVERLAP):
    if strategy not in {"auto", "custom", "hierarchy"}:
        raise ValueError("切片策略必须是 auto、custom 或 hierarchy")
    if not isinstance(max_chars, int) or not 32 <= max_chars <= 800 or not isinstance(overlap_chars, int) or not 0 <= overlap_chars < max_chars:
        raise ValueError("切片长度须为32至800，重叠须小于切片长度")
    if not content:
        return []
    chunks = []
    start = 0
    while start < len(content):
        end = min(start + max_chars, len(content))
        if end < len(content) and strategy != "custom":
            pattern = r"\n(?=#{1,6} )|\n\s*\n" if strategy == "hierarchy" else r"\n\s*\n"
            boundaries = [start + m.start() for m in re.finditer(pattern, content[start:end])]
            usable = [boundary for boundary in boundaries if boundary > start + max(overlap_chars, max_chars // 2)]
            if usable:
                end = usable[-1]
        chunks.append((len(chunks), start, end, content[start:end]))
        if end == len(content):
            break
        start = max(start + 1, end - overlap_chars)
    return chunks


def split_material(content, options=None):
    """Slice lecture text the way the upload dialog asks.

    ``auto`` uses a fixed 800-character window. ``hierarchy`` splits on Markdown
    headings. ``custom`` uses the chosen delimiter, length, overlap and cleaning.
    """
    options = options or {}
    strategy = options.get('strategy') or 'auto'
    if strategy not in {'auto', 'custom', 'hierarchy'}:
        raise ValueError('切片方式不正确')
    text = content or ''
    if strategy == 'custom' and options.get('strip_urls'):
        text = _URL.sub(' ', text)
    if strategy == 'custom' and options.get('collapse_ws'):
        text = ' '.join(text.split())
    if strategy == 'hierarchy':
        maximum, overlap = _window_size(options.get('max_chars'), options.get('overlap_pct'), True)
        return _hierarchy(text, maximum, overlap)
    if strategy == 'custom':
        maximum, overlap = _window_size(options.get('max_chars'), options.get('overlap_pct'), False)
        return _window(text, maximum, overlap, options.get('delimiter') or '')
    return _window(text, CHUNK_SIZE, CHUNK_OVERLAP, '')


def _window_size(max_chars, overlap_pct, hierarchy):
    try:
        maximum = int(max_chars or 0)
        percent = int(overlap_pct or 0)
    except (TypeError, ValueError):
        raise ValueError('切片长度或重叠度不正确')
    if hierarchy and maximum <= 0:
        return CHUNK_SIZE, CHUNK_OVERLAP
    if maximum < 100:
        maximum = 100
    if maximum > 2000:
        maximum = 2000
    overlap = maximum * percent // 100
    if overlap < 0:
        overlap = 0
    if overlap > maximum // 2:
        overlap = maximum // 2
    return maximum, overlap


def _hierarchy(src, maximum, overlap):
    parts = []
    buffer = []

    def flush():
        text = '\n'.join(buffer).strip()
        buffer.clear()
        if text:
            parts.append(text)

    for line in src.split('\n'):
        trimmed = line.strip()
        if trimmed.startswith('# ') or trimmed.startswith('## ') or trimmed.startswith('### '):
            flush()
        buffer.append(line)
    flush()
    if not parts:
        return _window(src, maximum, overlap, '')
    pieces = []
    offset = 0
    for part in parts:
        index = src.find(part, offset)
        if index < 0:
            index = offset
        if len(part) > maximum:
            for _, start, end, value in _window(part, maximum, overlap, ''):
                pieces.append((len(pieces), index + start, index + end, value))
        else:
            pieces.append((len(pieces), index, index + len(part), part))
        offset = index + len(part)
    return pieces


def _window(src, maximum, overlap, delimiter):
    if not src:
        return []
    if overlap >= maximum:
        overlap = maximum // 10
    pieces = []
    start = 0
    length = len(src)
    while start < length:
        end = min(start + maximum, length)
        if end < length:
            end = _break_at(src, start, end, delimiter)
        if end <= start:
            end = min(start + maximum, length)
        text = src[start:end].strip()
        if text:
            pieces.append((len(pieces), start, end, text))
        if end >= length:
            break
        nxt = end - overlap
        start = end if nxt <= start else nxt
    return pieces


def _break_at(src, start, end, delimiter):
    segment = src[start:end]
    if delimiter == 'blank':
        markers = ['\n\n']
    elif delimiter == 'newline':
        markers = ['\n']
    elif delimiter == 'period':
        markers = ['。', '.']
    else:
        markers = ['\n\n', '\n', '。', '！', '？', '.', '!', '?']
    minimum = len(segment) // 5
    for marker in markers:
        position = segment.rfind(marker)
        if position >= minimum:
            return start + len(segment[:position]) + len(marker)
    return end


def insert_chunks(connection, material_id, class_id, content, strategy="auto", max_chars=CHUNK_SIZE, overlap_chars=CHUNK_OVERLAP):
    connection.executemany(
        """INSERT INTO knowledge_chunks
           (material_id, class_id, chunk_index, start_offset, end_offset, content, strategy)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        [(material_id, class_id, index, start, end, text, strategy)
         for index, start, end, text in split_chunks(content, strategy, max_chars, overlap_chars)],
    )


def backfill_chunks(connection):
    """Idempotently index every pre-existing knowledge entry."""
    rows = connection.execute(
        """SELECT e.material_id, e.class_id, e.content FROM knowledge_entries e
           WHERE NOT EXISTS (SELECT 1 FROM knowledge_chunks c WHERE c.material_id = e.material_id)"""
    ).fetchall()
    for row in rows:
        insert_chunks(connection, row["material_id"], row["class_id"], row["content"])
    return len(rows)
