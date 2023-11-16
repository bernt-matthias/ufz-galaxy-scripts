"""
install (i.e. cache) containers for a set of tools

tools can be selected by basic string matching (--filter)
or version (--latest)
"""

import argparse
import logging
import os.path
import re
import sys
from typing import List
from bioblend.toolshed import ToolShedInstance
from yaml import load, dump

NEWLINE = "\n"

parser = argparse.ArgumentParser(description='List / install containers')
parser.add_argument('--url', type=str, action='store', default="https://toolshed.g2.bx.psu.edu/", help='Toolshed URL')
parser.add_argument('--category', type=str, action='store', required=True, default=None, help='Category name')
parser.add_argument('--owner', type=str, action='store', required=False, default=None, help='Category name')
parser.add_argument('--latest', action='store_true', default=False, help='consider only the latest version of the tool')
args = parser.parse_args()

ts = ToolShedInstance(url=args.url)
categories = ts.categories.get_categories()
category_id = [c for c in categories if c["name"] == args.category][0]["id"]
repositories = ts.categories.get_repositories(category_id)

for repo in repositories["repositories"]:
    if repo['deprecated']:
        continue
    if args.owner and repo["owner"] != args.owner:
        continue
    
    sys.stderr.write(f'# {repo["name"]}\n')
    sys.stderr.write(f'# \t{repo["description"]}\n')
    sys.stderr.write(f'# \t{repo["homepage_url"]}\n')
    sys.stderr.write(f'# \t{repo["remote_repository_url"]}\n')
    revisions = []
    for m in repo["metadata"].values():
        revisions.append(f'  - {m["changeset_revision"]}  # {m["numeric_revision"]}')
        if args.latest:
            break

    print(f'''
- name: {repo["name"]}
  owner: {repo["owner"]}
  tool_panel_section_label: {args.category}
  tool_shed_url: {args.url}
  revisions:
{NEWLINE.join(revisions)}
  install_tool_dependencies: False
  install_repository_dependencies: False
  install_resolver_dependencies: False
''')