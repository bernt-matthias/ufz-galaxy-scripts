import argparse
import logging
import os
import os.path

from bioblend.galaxy import GalaxyInstance

USER_BATCH_SIZE = 10000

parser = argparse.ArgumentParser(
    description="List or remove user import libraries of users deleted users"
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
    "--all-users",
    action="store_true",
    default=False,
    help="Process histories of all users, default only users not in LDAP",
)
parser.add_argument(
    "--delete",
    action="store_true",
    default=False,
    help="Really delete",
)
parser.add_argument(
    "-log",
    "--loglevel",
    choices=["debug", "info", "warning", "error"],
    default="info",
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
gi = GalaxyInstance(url=args.url, key=key)

users = gi.users.get_users()
usernames = set(user.get("username") for user in users)

user_data_library = gi.libraries.get_libraries(name="user_data")[0]
root_folder = gi.libraries.show_folder(
    library_id=user_data_library["id"], folder_id=user_data_library["root_folder_id"]
)


def process(user_data_library, folder):
    cnt = 0
    folder_id = folder["id"]
    item_count = gi.folders.show_folder(folder_id=folder_id)["item_count"]
    folder_details = gi.folders.show_folder(
        folder_id=folder_id, contents=True, limit=item_count
    )

    metadata = folder_details["metadata"]
    full_path = [c[1] for c in metadata["full_path"]]
    full_path_str = "/".join(full_path)
    for content in folder_details["folder_contents"]:
        if content["type"] == "folder":
            if len(full_path) == 1:
                if not args.all_users and content["name"] in usernames:
                    logger.debug(f"Skip {content['name']}")
                    continue
                else:
                    logger.info(f"Consider {content['name']}")
            cnt += 1
            if args.delete:
                gi.folders.delete_folder(content["id"])
                logger.info(f"Deleted folder '{content['name']}' in {full_path_str}")
            else:
                logger.info(
                    f"Could delete folder '{content['name']}' in {full_path_str}"
                )
        else:
            logger.error(
                f"Unknown content type: {content['type']} in {full_path=} {metadata=}"
            )
    return cnt


cnt = process(user_data_library, root_folder)

if args.delete:
    if cnt > 0:
        logger.warning(f"Deleted {cnt} user folders")
else:
    logger.info(f"Could delete {cnt} user folders")
