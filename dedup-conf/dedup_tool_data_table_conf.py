#!/usr/bin/env python3
"""Remove duplicate <table> entries from shed_tool_data_table_conf.xml.

Duplicate rule
--------------
Two top-level <table> entries are duplicates iff the path of their
<file> child element is the same (same value of the path attribute).
The first occurrence of each duplicate group is kept.

The file is re-serialized with 4-space indentation, mirroring the
input's XML declaration and trailing-newline state. Note: XML comments
are not preserved by ElementTree.

Idempotent: running the script on an already clean file changes nothing.

Usage
-----
    python3 dedup_tool_data_table_conf.py INPUT [OUTPUT]

If OUTPUT is omitted, INPUT + '.dedup' is used.
"""

import sys
import xml.etree.ElementTree as ET


def entry_key(table):
    """Duplicate key: the path attribute of the <file> child element."""
    file_el = table.find('file')
    assert file_el is not None, 'table without <file> child'
    return file_el.get('path')


def dedup(path):
    tree = ET.parse(path)
    root = tree.getroot()
    entries = root.findall('table')

    seen = set()
    kept = 0
    for entry in entries:
        key = entry_key(entry)
        if key in seen:
            root.remove(entry)
        else:
            seen.add(key)
            kept += 1

    stats = {'table total': len(entries),
             'duplicates removed': len(entries) - kept,
             'table remaining': kept}
    return tree, stats


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    inp = sys.argv[1]
    outp = sys.argv[2] if len(sys.argv) > 2 else inp + '.dedup'

    with open(inp, 'rb') as f:
        raw = f.read()
    tree, stats = dedup(inp)
    ET.indent(tree, space='    ')
    body = ET.tostring(tree.getroot(), encoding='unicode')
    with open(outp, 'w', encoding='utf-8', newline='\n') as f:
        if raw.startswith(b'<?xml'):
            f.write('<?xml version="1.0" ?>\n')
        f.write(body)
        if raw.endswith(b'\n'):
            f.write('\n')

    print(f'input:  {inp}')
    print(f'output: {outp}')
    for k, v in stats.items():
        print(f'  {k}: {v}')


if __name__ == '__main__':
    main()
