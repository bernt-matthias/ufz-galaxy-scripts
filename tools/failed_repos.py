import argparse
import logging
import os
import sys

from bioblend.galaxy import GalaxyInstance
from bioblend.galaxy.toolshed import ToolShedClient


ERROR_STATUS = "Error"

parser = argparse.ArgumentParser(
    description="Get all tool shed repositories with error installation status and optionally reset them"
)
parser.add_argument(
    "--url", type=str, action="store", required=True, default=None, help="Galaxy URL"
)
parser.add_argument(
    "--key",
    type=str,
    action="store",
    required=False,
    default=None,
    help="API key, better set API_KEY env var",
)
parser.add_argument(
    "--reset",
    action="store_true",
    default=False,
    help="Reset the broken repositories, like the 'Reset' button in the Galaxy admin "
    "interface: the failed installation is uninstalled and removed from disk, so that "
    "the repository can be installed again afterwards",
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

key = os.environ.get("GALAXY_API_KEY", args.key)
galaxy_instance = GalaxyInstance(url=args.url, key=key)
tool_shed_client = ToolShedClient(galaxy_instance)

# Get the list of installed tools
tool_shed_repos = tool_shed_client.get_repositories()
# Filter repositories where the installation failed
failed_tools = [repo for repo in tool_shed_repos if repo["status"] == ERROR_STATUS]

for tool in failed_tools:
    sys.stderr.write(f"- failed {tool['name']} (Owner: {tool['owner']})\n")

if not args.reset or not failed_tools:
    if args.reset:
        logger.info("No broken repositories found, nothing to reset")
    sys.exit(0)

not_reset = []
for tool in failed_tools:
    if not tool["changeset_revision"]:
        logger.error(
            "Cannot reset %s (Owner: %s), the repository record has no changeset revision",
            tool["name"],
            tool["owner"],
        )
        not_reset.append(tool)
        continue
    logger.info(
        "Resetting %s (Owner: %s, revision: %s)",
        tool["name"],
        tool["owner"],
        tool["changeset_revision"],
    )
    try:
        tool_shed_client.uninstall_repository_revision(
            name=tool["name"],
            owner=tool["owner"],
            changeset_revision=tool["changeset_revision"],
            tool_shed_url=tool["tool_shed"],
            remove_from_disk=True,
        )
    except Exception as e:
        logger.error(
            "Failed to reset %s (Owner: %s): %s", tool["name"], tool["owner"], e
        )
        not_reset.append(tool)

logger.info(
    "Reset %d of %d broken repositories",
    len(failed_tools) - len(not_reset),
    len(failed_tools),
)

if not_reset:
    plural = "repositories" if len(not_reset) > 1 else "repository"
    sys.stderr.write(
        f"{len(not_reset)} {plural} could not be reset, "
        "they still need to be repaired or removed manually\n"
    )
    sys.exit(1)
