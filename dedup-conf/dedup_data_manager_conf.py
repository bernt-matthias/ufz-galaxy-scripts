#!/usr/bin/env python3
"""Remove duplicate <data_manager> entries from shed_data_manager_conf.xml.

Duplicate rule
--------------
Two top-level <data_manager> entries are duplicates iff ALL of their
attribute name/value pairs AND the <tool> element they contain are
identical (same attributes, same child tag contents). Entries with
identical attributes but a different contained tool are NOT duplicates
and are all kept. The first occurrence of each duplicate group is kept.

The file is re-serialized with 4-space indentation, mirroring the
input's XML declaration (this file has none) and trailing-newline
state. Note: XML comments are not preserved by ElementTree.

Idempotent: running the script on an already clean file changes nothing.

Usage
-----
    python3 dedup_data_manager_conf.py INPUT [OUTPUT]

If OUTPUT is omitted, INPUT + '.dedup' is used.
"""

import sys
import xml.etree.ElementTree as ET


def tool_key(tool):
    """Equality key for a <tool> element: attributes + child contents."""
    children = [(c.tag, tuple(sorted(c.attrib.items())), c.text or '')
                for c in tool]
    return (tool.tag, tuple(sorted(tool.attrib.items())), tuple(children))


def entry_key(entry):
    """Duplicate key: all attribute pairs + the contained <tool>.

    Attribute order is insignificant in XML, so pairs are sorted.
    """
    tool = entry.find('tool')
    assert tool is not None, 'data_manager without <tool> child'
    return (tuple(sorted(entry.attrib.items())), tool_key(tool))


def dedup(path):
    tree = ET.parse(path)
    root = tree.getroot()
    entries = root.findall('data_manager')

    seen = set()
    kept = 0
    for entry in entries:
        key = entry_key(entry)
        if key in seen:
            root.remove(entry)
        else:
            seen.add(key)
            kept += 1

    stats = {'data_manager total': len(entries),
             'duplicates removed': len(entries) - kept,
             'data_manager remaining': kept}
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
