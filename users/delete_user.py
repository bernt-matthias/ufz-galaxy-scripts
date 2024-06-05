import argparse
import logging

from bioblend.galaxy import GalaxyInstance
from bioblend.galaxy.users import UserClient


parser = argparse.ArgumentParser(description="Delete a user")
parser.add_argument(
    "--url", type=str, action="store", required=True, default=None, help="Galaxy URL"
)
parser.add_argument(
    "--key", type=str, action="store", required=True, default=None, help="API key"
)
parser.add_argument(
    "--username",
    type=str,
    action="store",
    required=True,
    default=None,
    help="User name",
)
parser.add_argument(
    "--purge",
    action="store_true",
    default=False,
    help="Purge user",
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

user_client = UserClient(galaxy_instance=galaxy_instance)
users = user_client.get_users(f_name=args.username)
users = [u for u in users if u.get("username") == args.username]
assert len(users) == 1, f"Found {len(users)} users with name {args.username}"
uid = users[0]["id"]

user_client.delete_user(uid)
if args.purge:
    user_client.delete_user(uid, purge=args.purge)
