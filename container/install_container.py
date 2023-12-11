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

from bioblend.galaxy import GalaxyInstance
from bioblend.galaxy.tool_dependencies import ToolDependenciesClient
from bioblend.galaxy.tools import ToolClient
from bioblend.galaxy.container_resolution  import ContainerResolutionClient
from galaxy.tool_util.version import parse_version
from galaxy.util.tool_version import remove_version_from_guid
import packaging.version 


def get_tool_list(galaxy_instance: GalaxyInstance, include: List[str], exclude: List[str], latest: bool):
    """
    get a list of tool IDs from a galaxy instance

    include are applied and if desired only the latest version of each tool is returned
    """
    tool_client = ToolClient(galaxy_instance)
    tools = tool_client.get_tools()
    
    tool_versions = {}
    for tool in tools:
        tool_id = tool["id"]
        if include and not any([re.search(f, tool_id) for f in include]):
            continue
        if exclude and any([re.search(f, tool_id) for f in exclude]):
            continue
        tool_id = remove_version_from_guid(tool_id) or tool_id
    
        if tool_id not in tool_versions:
            tool_versions[tool_id] = []
        try:
            version = parse_version(tool["version"])
        except:
            logger.error(f"could not parse version {version} of tool {tool}")
            continue
        tool_versions[tool_id].append((version, tool["id"]))
    tool_list = []
    for tool_id in tool_versions:
        tool_versions[tool_id] = sorted(tool_versions[tool_id], reverse=True)
        if latest:
            tool_versions[tool_id] = tool_versions[tool_id][:1]
        for t in tool_versions[tool_id]:
            tool_list.append(t[1])
    return tool_list

parser = argparse.ArgumentParser(description='List / install containers')
parser.add_argument('--url', type=str, action='store', required=True, default=None, help='Galaxy URL')
parser.add_argument('--key', type=str, action='store', required=True, default=None, help='API key')
parser.add_argument(
    '--include',
    type=str,
    action='append',
    dest="include",
    default=[],
    help='include tool id by searching for regexp, if any filter applies a tool is included'
)
parser.add_argument(
    '--exclude',
    type=str,
    action='append',
    dest="exclude",
    default=[],
    help='filter tool id by searching for regexp, if any filter applies a tool is excluded'
)
parser.add_argument('--latest', action='store_true', default=False, help='consider only the latest version of the tool')
parser.add_argument('--install_container', action='store_true', default=False, help='install the container')
parser.add_argument( '-log',
                     '--loglevel',
                     choices=['debug', 'info', 'warning', 'error'],
                     default='warning',
                     help='Provide logging level. Example --loglevel debug, default=warning' )
args = parser.parse_args()

logging.getLogger().setLevel(logging.WARNING)
logger = logging.getLogger(__name__)
# Set the log level for your logger to the desired level (e.g., INFO)
logger.setLevel(args.loglevel.upper())

# Create a handler for logging output (e.g., console handler)
handler = logging.StreamHandler()
logger.addHandler(handler)

# Add a formatter to the handler (optional)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

galaxy_instance = GalaxyInstance(url=args.url, key=args.key)

# get tools (matching filters and latest arguments)
tool_list = get_tool_list(galaxy_instance, args.include, args.exclude, args.latest)

new_containers = set()
container_resolution_client = ContainerResolutionClient(galaxy_instance = galaxy_instance)
for tool in tool_list:
    logger.debug(f"Checking {tool}")
    res = container_resolution_client.resolve_toolbox(tool_ids = [tool])
    container = None
    for i, r in enumerate(res):
        tool_id = r['tool_id']
        container = r["status"].get("environment_path")
    
    if container is None:
        logger.debug(f"No container for for {tool}")
        continue

    if os.path.exists(container):
        logger.debug(f"Container for {tool} already installed {os.path.basename(container)}")
        continue

    res = container_resolution_client.resolve_toolbox(tool_ids = [tool], install=args.install_container)
    for i, r in enumerate(res):
        tool_id = r['tool_id']
        new_container = r["status"].get("environment_path")

        if new_container and os.path.exists(new_container):
            print(f"Installed {new_container}")
        elif not args.install_container:
            logger.warning(f"Skipped installation of {new_container}")
        else:
            logger.error(f"Could not install container for {tool} {container=} {new_container=}")
