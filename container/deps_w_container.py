"""
remove unused conda dependencies
"""

import argparse
import logging
import os
import os.path
import shutil

from bioblend.galaxy import GalaxyInstance
from bioblend.galaxy.container_resolution import ContainerResolutionClient
from bioblend.galaxy.tool_dependencies import ToolDependenciesClient

parser = argparse.ArgumentParser(description="List / install containers")
parser.add_argument(
    "--url", type=str, action="store", required=True, default=None, help="Galaxy URL"
)
parser.add_argument(
    "--key", type=str, action="store", required=False, default=None, help="API key, better set API_KEY env var"
)
parser.add_argument(
    "--remove",
    action="store_true",
    default=False,
    help="remove unused dependencies, default: just list",
)
parser.add_argument(
    '-log',
    '--loglevel',
    choices=['debug', 'info', 'warning', 'error'],
    default='warning',
    help='Provide logging level. Example --loglevel debug, default=warning'
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
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

key = os.environ.get('GALAXY_API_KEY', args.key)
galaxy_instance = GalaxyInstance(url=args.url, key=key)
tool_dependency_client = ToolDependenciesClient(galaxy_instance=galaxy_instance)

# get mapping from conda envs to tools using it
tb = tool_dependency_client.summarize_toolbox(index_by="tools")
condaenv2tools = {}
for t in tb:
    # status contains the conda dependencioes for the requirements can be 
    # - NullDependency: unresolved
    # - CondaDependency: resolved dependency for 1 requirement
    # - MergedCondaDependency: resolved conda dependency for all requirements (also if there is only one)
    status = [_ for _ in t["status"] if _['model_class'] == 'MergedCondaDependency']
    if len(status) == 0:
        continue
    for tool_id in t['tool_ids']:
        conda = status[0].get("environment_path")
        if not conda:
            continue
        try:
            condaenv2tools[conda].append(tool_id)
        except KeyError:
            condaenv2tools[conda] = [tool_id]

logger.info(f"Found {len(condaenv2tools)} conda environments")

# check if all tools using a conda env have a installed container
container_resolution_client = ContainerResolutionClient(galaxy_instance=galaxy_instance)
for condaenv in condaenv2tools:
    condaenv_base = os.path.basename(condaenv)
    if condaenv.endswith("/_galaxy_"):
        continue
    tools = condaenv2tools[condaenv]
    has_container = 0
    for tool in tools:
        res = container_resolution_client.resolve_toolbox(tool_ids=[tool])
        for i, r in enumerate(res):
            container = r["status"].get("environment_path")
            if container and os.path.exists(container):
                has_container += 1
            else:
                logger.debug(f"{condaenv_base} no container for tool {tool}")
    logger.debug(f"{condaenv_base} -> {has_container == len(tools)} (coverage {has_container}/{len(tools)})")
    if has_container == len(tools):
        if args.remove:
            print(f"removing {condaenv}")
            try:
                shutil.rmtree(condaenv)
            except Exception as e:
                logger.error(f"could not remove {condaenv}: {e}")
            print(f"removed {condaenv}")
        else:
            print(f"would remove {condaenv}")
