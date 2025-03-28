import argparse
import logging
import os
import sys

from bioblend.galaxy import GalaxyInstance


parser = argparse.ArgumentParser(description="Get all with error installation status")
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

# Get the list of installed tools
tool_shed_repos = galaxy_instance.toolShed.get_repositories()
# Filter repositories where the installation failed
failed_tools = [repo for repo in tool_shed_repos if repo["status"] == "Error"]

for tool in failed_tools:
    sys.stderr.write(f"- failed {tool['name']} (Owner: {tool['owner']})\n")
