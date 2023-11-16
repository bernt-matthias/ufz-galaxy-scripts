"""
Check for tools that are not covered by conda or containers
"""

import argparse
import logging
import os.path
import shutil
import sys

from bioblend.galaxy import GalaxyInstance
from bioblend.galaxy.container_resolution  import ContainerResolutionClient
from bioblend.galaxy.tool_dependencies import ToolDependenciesClient

parser = argparse.ArgumentParser(description="List / install containers")
parser.add_argument(
    "--url", type=str, action="store", required=True, default=None, help="Galaxy URL"
)
parser.add_argument(
    "--key", type=str, action="store", required=True, default=None, help="API key"
)
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
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)


galaxy_instance = GalaxyInstance(url=args.url, key=args.key)
tool_dependency_client = ToolDependenciesClient(galaxy_instance=galaxy_instance)

# get mapping from conda envs to tools using it
tb = tool_dependency_client.summarize_toolbox(index_by = "tools")
tool_stats = {}
for t in tb:
    status = t["status"]
    for tool_id in t['tool_ids']:
        tool_stats[tool_id] = {'requirements': t['requirements']}
        if len(status) == 0:
            conda = None
        else:
            conda = status[0].get("environment_path")
        tool_stats[tool_id] = {'conda': conda, 'requirements': t['requirements']}

conda_envs = set([x['conda'] for x in tool_stats.values() if 'conda' in x and x['conda']])
logger.info(f"Found {len(conda_envs)} conda environments")
conda_prefix = os.path.commonprefix(list(conda_envs))
conda_envs = set([os.path.basename(e) for e in conda_envs])
conda_dirs = set(os.listdir(conda_prefix))

for u in conda_dirs.difference(conda_envs):
    if u == "_galaxy_":
        continue
    if not os.path.isdir(os.path.join(conda_prefix, u)):
        continue
    print(f"Potentially unused: {u}")
# for c in set([x['conda'] for x in tool_stats.values() if 'conda' in x]):
#     logger.info(f"\t{c}")

# check if all tools using a conda env have an installed container
container_resolution_client = ContainerResolutionClient(galaxy_instance = galaxy_instance)
res = container_resolution_client.resolve_toolbox()
for r in res:
    tool_id = r["tool_id"]
    container = r["status"].get("environment_path")
    if not (container and os.path.exists(container)):
        container = None
    if tool_id not in tool_stats:
        tool_stats[tool_id] = {}
    tool_stats[tool_id]['container'] = container

logger.info(f"Found {len(set([x['container'] for x in tool_stats.values() if 'container' in x and x['container']]))} containers")
# TODO check if there are extra/unused containers envs
# for c in set([x['container'] for x in tool_stats.values() if 'container' in x]):
#     logger.info(f"\t{c}")

for tool_id in tool_stats:
    stats = tool_stats[tool_id]
    # if stats.get("container") and stats.get("conda"):
    #     logger.error(f"{tool_id} has conda {stats.get('conda')} and container {stats.get('container')}")
    if not stats.get("container") and not stats.get("conda") and len(stats.get("requirements", [])) > 0:
        print(f"{tool_id} has no conda and no container")
    # logger.info(f"{tool_id} -> {tool_stats[tool_id]}")