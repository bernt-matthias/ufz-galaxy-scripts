"""
Find and delete dangling library data sets

A dangling library data set is a non-deleted dataset
that is contained in a subtree with a root that is a
deleted folder/library

Therefore the script recursively crawls all deleted
and nondeleted libraries and contained folders.
"""

import argparse
import logging
import os
import os.path

import humanize
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
    "--delete",
    action="store_true",
    default=False,
    help="Really delete",
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
gi = GalaxyInstance(url=args.url, key=key)

users = gi.users.get_users()
usernames = set(user.get("username") for user in users)


def recurse(library, folder, deleted, folder_cnt, file_cnt, file_size):
    folder_id = folder["id"]
    # determine item_count and deleted (which are both only given if called wo contents=True)
    folder_details = gi.folders.show_folder(folder_id=folder_id, include_deleted=True)
    item_count = folder_details["item_count"]
    deleted = folder_details["deleted"] or deleted
    if item_count == 0:
        return folder_cnt, file_cnt, file_size
    folder_details = gi.folders.show_folder(
        folder_id=folder_id, contents=True, limit=item_count, include_deleted=True
    )

    metadata = folder_details["metadata"]
    full_path = [c[1] for c in metadata["full_path"]]
    full_path_str = "/".join(full_path)
    for content in folder_details["folder_contents"]:
        if content["type"] == "folder":
            folder_cnt, file_cnt, file_size = recurse(
                library, content, deleted, folder_cnt, file_cnt, file_size
            )

        if content["type"] == "folder":
            if not content["deleted"] and deleted:
                folder_cnt += 1
                if args.delete:
                    gi.folders.delete_folder(content["id"])
                logger.debug(f"Dangling folder '{content['name']}' in {full_path_str}")
        elif content["type"] == "file":
            if not content["deleted"] and deleted:
                file_cnt += 1
                file_size += content["raw_size"]
                if args.delete:
                    gi.libraries.delete_library_dataset(library["id"], content["id"], purged=True)
                logger.debug(
                    f"Dangling dataset '{content['name']}' ({humanize.naturalsize(content['raw_size'], binary=False)}) in {full_path_str}"
                )
        else:
            logger.error(
                f"Unknown content type: {content['type']} in {full_path=} {metadata=}"
            )
    return folder_cnt, file_cnt, file_size


libraries = gi.libraries.get_libraries(deleted=None)
for library in libraries:
    root_folder = gi.libraries.show_folder(
        library_id=library["id"], folder_id=library["root_folder_id"]
    )
    logger.info(f"Processing library {library['name']}")
    folder_cnt, file_cnt, file_size = recurse(library, root_folder, library["deleted"], 0, 0, 0)
    # TODO  check root folder

    if folder_cnt + file_cnt + file_size > 0:
        logger.warning(
            f"{library['name']} Found {folder_cnt} folders {file_cnt} files {humanize.naturalsize(file_size, binary=False)}"
        )
