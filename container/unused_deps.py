"""
remove unused dependencies
"""

import argparse
import os

from bioblend.galaxy import GalaxyInstance
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
args = parser.parse_args()

key = os.environ.get('API_KEY', args.key)
galaxy_instance = GalaxyInstance(url=args.url, key=key)
tool_dependency_client = ToolDependenciesClient(galaxy_instance=galaxy_instance)
unused_paths = tool_dependency_client.unused_dependency_paths()

# filter _galaxy_, https://github.com/galaxyproject/galaxy/pull/16460
unused_paths = [u for u in unused_paths if u.endswith("/_galaxy_")]

for u in unused_paths:
    if args.remove:
        print(f"removing {u}")
        tool_dependency_client.delete_unused_dependency_paths([u])
    else:
        print(f"unused {u}")
