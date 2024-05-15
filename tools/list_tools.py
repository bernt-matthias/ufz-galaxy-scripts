import argparse
import logging

import yaml

from bioblend.galaxy import GalaxyInstance
from bioblend.galaxy.tools import ToolClient


parser = argparse.ArgumentParser(
    description="Get all installed tools"
)
parser.add_argument(
    "--url", type=str, action="store", required=True, default=None, help="Galaxy URL"
)
parser.add_argument(
    "--key", type=str, action="store", required=True, default=None, help="API key"
)
parser.add_argument(
    "-log",
    "--loglevel",
    choices=["debug", "info", "warning", "error"],
    default="warning",
    help="Provide logging level. Example --loglevel debug, default=warning",
)
args = parser.parse_args()

logging.getLogger().setLevel(logging.WARNING)
logger = logging.getLogger(__name__)
# Set the log level for your logger to the desired level (e.g., INFO)
logger.setLevel(args.loglevel.upper())

# Create a handler for logging output (e.g., console handler)
handler = logging.StreamHandler()
logger.addHandler(handler)

# Add a formatter to the handler (optional)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)

galaxy_instance = GalaxyInstance(url=args.url, key=args.key)
tool_client = ToolClient(galaxy_instance)
tools = tool_client.get_tools()

tool_list = {}
for i, tool in enumerate(tools):
    if not tool.get("tool_shed_repository"):
        continue
    if not tool.get("panel_section_name"):
        if tool.get('model_class') == 'DataManagerTool':
            tool["panel_section_name"] = "Data Managers"
        else:
            log.error(f"Missing tool panel section for {tool}")
            sys.exit(1)

    name = tool['tool_shed_repository']['name']
    owner = tool['tool_shed_repository']['owner']
    revision = tool['tool_shed_repository']['changeset_revision']
    section = tool['panel_section_name']

    if (name, owner) not in tool_list:
        tool_list[(name, owner)] = {
            'name': name,
            'owner': owner,
            'tool_panel_section_label': section,
            'revisions': set()
        }
    tool_list[(name, owner)]['revisions'].add(revision)

for tool in tool_list:
    tool_list[tool]['revisions'] = list(tool_list[tool]['revisions'])

with open("tool_list.yaml.lock", "w") as lock_f:
    lock_f.write(
        yaml.dump(
            {
                'install_repository_dependencies': True,
                'install_resolver_dependencies': False,
                'install_tool_dependencies': False,
                'tools': list(tool_list.values())
            }
        )
    )

for tool in tool_list:
    del tool_list[tool]['revisions']

with open("tool_list.yaml", "w") as lock_f:
    lock_f.write(
        yaml.dump(
            {
                'install_repository_dependencies': True,
                'install_resolver_dependencies': False,
                'install_tool_dependencies': False,
                'tools': list(tool_list.values())
            }
        )
    )