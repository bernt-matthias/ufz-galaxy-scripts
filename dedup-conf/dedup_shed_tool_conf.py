#!/usr/bin/env python3
"""Remove duplicate entries from a Galaxy shed_tool_conf.xml file.

Two passes
----------
1. Merge the contents of duplicate sections: all sections with identical
   id, name and version are merged into the first occurrence. All child
   elements of the redundant copies are moved into the merged section,
   in document order. (A missing `version` attribute counts as the
   empty string.)
2. Deduplicate each section: a <tool> entry is a duplicate of an earlier
   entry in the same section iff ALL of its attributes AND the contents
   of all child tags are equal. The first occurrence is kept, later
   identical entries are removed. Entries with the same guid but
   different content (e.g. a new changeset revision in the `file`
   attribute) are NOT duplicates and are all kept.

The file is re-serialized with the original 4-space indentation and XML
declaration. No tool entry is ever modified.

Idempotent: running the script on an already clean file changes nothing.

Usage
-----
    python3 dedup_shed_tool_conf.py INPUT [OUTPUT]

If OUTPUT is omitted, INPUT + '.dedup' is used.
"""

import sys
import xml.etree.ElementTree as ET


def section_key(sec):
    """Identity of a section: id + name + version ('' if absent)."""
    return (sec.get('id'), sec.get('name'), sec.get('version') or '')


def tool_key(tool):
    """Equality key for a tool entry: attributes + child tag contents."""
    children = [(c.tag, tuple(sorted(c.attrib.items())), c.text or '')
                for c in tool]
    return (tool.tag, tuple(sorted(tool.attrib.items())), tuple(children))


def merge_duplicate_sections(root):
    """Pass 1: merge all sections with the same id, name and version.

    The first occurrence is kept; all child elements of the redundant
    copies are moved into it, in document order. Returns the list of
    merged sections in first-seen order.
    """
    merged = {}  # section key -> canonical section element
    for sec in root.findall('section'):
        key = section_key(sec)
        target = merged.get(key)
        if target is None:
            # First time we see this section: it becomes canonical.
            merged[key] = sec
            target = sec
        if target is not sec:
            # Redundant copy: move all its children into the canonical one.
            for child in list(sec):
                sec.remove(child)
                target.append(child)
    return list(merged.values())


def remove_duplicate_tools(sec):
    """Pass 2: remove exact-duplicate tool entries from one section.

    The first occurrence of each entry is kept. Returns the number of
    entries removed.
    """
    seen = set()
    removed = 0
    for tool in list(sec):
        if tool.tag != 'tool':
            continue
        key = tool_key(tool)
        print(f"{key=}")
        if key in seen:
            sec.remove(tool)
            removed += 1
        else:
            seen.add(key)
    return removed


def dedup(path):
    tree = ET.parse(path)
    root = tree.getroot()
    sections_total = len(root.findall('section'))
    tools_total = sum(len(s) for s in root.findall('section'))

    # Pass 1: merge duplicate sections, then rebuild the toolbox with
    # only the merged sections (in first-seen order).
    sections = merge_duplicate_sections(root)
    for sec in list(root):
        root.remove(sec)
    for sec in sections:
        root.append(sec)

    # Pass 2: deduplicate the tool entries in each section.
    dups_removed = sum(remove_duplicate_tools(sec) for sec in sections)

    stats = {'sections_total': sections_total,
             'sections_remaining': len(sections),
             'tools_total': tools_total,
             'dups_removed': dups_removed,
             'tools_remaining': tools_total - dups_removed}
    return tree, stats


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    inp = sys.argv[1]
    outp = sys.argv[2] if len(sys.argv) > 2 else inp + '.dedup'

    tree, stats = dedup(inp)
    ET.indent(tree, space='    ')
    body = ET.tostring(tree.getroot(), encoding='unicode')
    with open(inp, 'rb') as f:
        had_trailing_newline = f.read()[-1:] == b'\n'
    with open(outp, 'w', encoding='utf-8', newline='\n') as f:
        f.write('<?xml version="1.0" ?>\n')
        f.write(body)
        if had_trailing_newline:
            f.write('\n')

    print(f'input:  {inp}')
    print(f'output: {outp}')
    for k, v in stats.items():
        print(f'  {k}: {v}')


if __name__ == '__main__':
    main()
