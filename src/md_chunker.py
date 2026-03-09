# import re
# from langchain_text_splitters import RecursiveCharacterTextSplitter
# from config import CHUNK_SIZE, CHUNK_OVERLAP, TABLE_ROWS_PRIMARY


# header_pattern = re.compile(r"^(#{1,6})\s+(.*)")


# def split_headers(text):

#     lines = text.split("\n")

#     sections = []
#     header_stack = []

#     current_content = []

#     for line in lines:

#         match = header_pattern.match(line)

#         if match:

#             if current_content:
#                 sections.append("\n".join(current_content).strip())

#             level = len(match.group(1))
#             title = match.group(2)

#             header_stack = header_stack[: level - 1]
#             header_stack.append(f"{'#'*level} {title}")

#             current_content = header_stack.copy()

#         else:
#             current_content.append(line)

#     if current_content:
#         sections.append("\n".join(current_content).strip())

#     return sections


# def detect_tables(lines):

#     tables = []
#     i = 0

#     while i < len(lines):

#         if lines[i].startswith("|"):

#             start = i

#             while i < len(lines) and lines[i].startswith("|"):
#                 i += 1

#             tables.append((start, i))

#         else:
#             i += 1

#     return tables


# def split_table(table_lines):

#     header = table_lines[:2]
#     rows = table_lines[2:]

#     chunks = []

#     for i in range(0, len(rows), TABLE_ROWS_PRIMARY):

#         part = rows[i:i + TABLE_ROWS_PRIMARY]

#         chunk = header + part

#         chunks.append("\n".join(chunk))

#     return chunks


# def process_section(section):

#     if len(section) <= CHUNK_SIZE:
#         return [section]

#     lines = section.split("\n")

#     header_lines = []

#     while lines and lines[0].startswith("#"):
#         header_lines.append(lines.pop(0))

#     header = "\n".join(header_lines)

#     tables = detect_tables(lines)

#     chunks = []
#     last = 0

#     splitter = RecursiveCharacterTextSplitter(
#         chunk_size=CHUNK_SIZE,
#         chunk_overlap=CHUNK_OVERLAP
#     )

#     for start, end in tables:

#         text_part = "\n".join(lines[last:start]).strip()

#         if text_part:

#             pieces = splitter.split_text(text_part)

#             for p in pieces:
#                 chunks.append(header + "\n" + p)

#         table_lines = lines[start:end]

#         table_chunks = split_table(table_lines)

#         for t in table_chunks:
#             chunks.append(header + "\n" + t)

#         last = end

#     remaining = "\n".join(lines[last:]).strip()

#     if remaining:

#         pieces = splitter.split_text(remaining)

#         for p in pieces:
#             chunks.append(header + "\n" + p)

#     return chunks


# def chunk_markdown(text):

#     sections = split_headers(text)

#     all_chunks = []

#     for section in sections:

#         chunks = process_section(section)

#         all_chunks.extend(chunks)

#     return all_chunks

import re
from langchain_text_splitters import RecursiveCharacterTextSplitter
from config import CHUNK_SIZE, CHUNK_OVERLAP

header_pattern = re.compile(r"^(#{1,6})\s+(.*)")


def split_markdown_tree(text):
    lines = text.split("\n")

    tree = []
    stack = []

    for line in lines:
        match = header_pattern.match(line)

        if match:
            level = len(match.group(1))

            node = {"level": level, "header": line, "content": []}

            while stack and stack[-1]["level"] >= level:
                stack.pop()

            if stack:
                stack[-1]["content"].append(node)
            else:
                tree.append(node)

            stack.append(node)

        else:
            if stack and line.strip():
                stack[-1]["content"].append(line)

    return tree


def flatten_section(node):
    text = [node["header"]]

    for item in node["content"]:
        if isinstance(item, dict):
            text.append(flatten_section(item))
        else:
            text.append(item)

    return "\n".join(text)


def detect_tables(lines):
    tables = []
    i = 0
    n = len(lines)
    # print("Inside detect tables: ",lines);

    while i < n - 1:

        line = lines[i].strip()
        next_line = lines[i + 1].strip()

        if line.startswith("|") and next_line.startswith("|") and "---" in next_line:

            start = i
            i += 2

            while i < n and lines[i].strip().startswith("|"):
                i += 1

            tables.append((start, i))

        else:
            i += 1

    return tables


def split_table_by_window(table_lines, header_context):

    table_header = table_lines[:2]
    rows = table_lines[2:]

    base = header_context + "\n" + "\n".join(table_header)

    chunks = []
    current_rows = []

    for row in rows:

        candidate_rows = current_rows + [row]

        candidate_chunk = base + "\n" + "\n".join(candidate_rows)

        if len(candidate_chunk) <= CHUNK_SIZE:

            current_rows = candidate_rows

        else:

            if current_rows:
                chunk = base + "\n" + "\n".join(current_rows)
                chunks.append(chunk)

            current_rows = [row]

    if current_rows:
        chunk = base + "\n" + "\n".join(current_rows)
        chunks.append(chunk)

    return chunks


def split_with_tables(text, header_context):

    print("text before splitting\n", text)

    lines = text.split("\n")
    print("text after splitting", lines)
    tables = detect_tables(lines)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks = []
    last = 0

    for start, end in tables:

        text_part = "\n".join(lines[last:start]).strip()

        if text_part:
            pieces = splitter.split_text(text_part)

            for p in pieces:
                chunks.append(header_context + "\n" + p)

        table_lines = lines[start:end]

        table_chunks = split_table_by_window(table_lines, header_context)

        chunks.extend(table_chunks)

        last = end

    remaining = "\n".join(lines[last:]).strip()

    if remaining:
        pieces = splitter.split_text(remaining)

        for p in pieces:
            chunks.append(header_context + "\n" + p)

    return chunks


def hierarchical_chunk(node, parent_headers=None):

    if parent_headers is None:
        parent_headers = []

    header_context = "\n".join(parent_headers + [node["header"]])

    full_text = flatten_section(node)

    if len(full_text) <= CHUNK_SIZE:
        return [full_text]

    chunks = []

    i = 0
    content = node["content"]

    while i < len(content):

        item = content[i]

        if isinstance(item, dict):

            chunks.extend(hierarchical_chunk(item, parent_headers + [node["header"]]))

            i += 1
            continue

        if isinstance(item, str) and item.strip().startswith("|"):

            table_lines = []

            while (
                i < len(content)
                and isinstance(content[i], str)
                and content[i].strip().startswith("|")
            ):
                table_lines.append(content[i])
                i += 1

            table_chunks = split_table_by_window(table_lines, header_context)

            chunks.extend(table_chunks)

            continue

        text_block = item.strip()

        if text_block:
            chunks.extend(split_with_tables(text_block, header_context))

        i += 1
    return chunks


def chunk_markdown(text):

    text = text.replace("\\n", " ")

    tree = split_markdown_tree(text)

    chunks = []

    for node in tree:
        chunks.extend(hierarchical_chunk(node))

    return chunks
