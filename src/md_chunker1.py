import re
from langchain_text_splitters import RecursiveCharacterTextSplitter
from config import CHUNK_SIZE, CHUNK_OVERLAP, TABLE_ROWS_PRIMARY


def split_headers(text):
    pattern = r"(?=^#{1,6} )"
    sections = re.split(pattern, text, flags=re.MULTILINE)
    return [s.strip() for s in sections if s.strip()]


def detect_tables(lines):
    tables = []
    i = 0

    while i < len(lines):
        if lines[i].startswith("|"):
            start = i
            while i < len(lines) and lines[i].startswith("|"):
                i += 1
            tables.append((start, i))
        else:
            i += 1

    return tables


def split_table(table_lines):

    header = table_lines[:2]
    rows = table_lines[2:]

    chunks = []

    for i in range(0, len(rows), TABLE_ROWS_PRIMARY):
        part = rows[i:i + TABLE_ROWS_PRIMARY]
        chunk = header + part
        chunks.append("\n".join(chunk))

    return chunks


def process_section(section):

    # if section already fits window → keep whole
    if len(section) <= CHUNK_SIZE:
        return [section]

    lines = section.split("\n")

    header = ""
    if lines[0].startswith("#"):
        header = lines[0]
        lines = lines[1:]

    tables = detect_tables(lines)

    chunks = []
    last = 0

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP
    )

    for start, end in tables:

        text_part = "\n".join(lines[last:start]).strip()

        if text_part:

            pieces = splitter.split_text(text_part)

            for p in pieces:
                chunks.append(header + "\n" + p)

        table_lines = lines[start:end]
        table_chunks = split_table(table_lines)

        for t in table_chunks:
            chunks.append(header + "\n" + t)

        last = end

    remaining = "\n".join(lines[last:]).strip()

    if remaining:

        pieces = splitter.split_text(remaining)

        for p in pieces:
            chunks.append(header + "\n" + p)

    return chunks


def chunk_markdown(text):

    sections = split_headers(text)

    all_chunks = []

    for section in sections:

        chunks = process_section(section)

        all_chunks.extend(chunks)

    return all_chunks

