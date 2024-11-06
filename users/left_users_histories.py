import argparse
import logging
import os
import os.path

from bioblend.galaxy import GalaxyInstance
from bioblend.galaxy.users import UserClient
from bioblend.galaxy.histories import HistoryClient
from ldap3 import Connection, SUBTREE

USER_BATCH_SIZE = 10000

parser = argparse.ArgumentParser(
    description="Get histories of users that left the UFZ, i.e. are not in the LDAP anymore"
)
parser.add_argument(
    "--url", type=str, action="store", required=True, default=None, help="Galaxy URL"
)
parser.add_argument(
    "--key", type=str, action="store", required=False, default=None, help="API key, better set API_KEY env var"
)
parser.add_argument(
    "--ldap-url",
    type=str,
    action="store",
    required=True,
    default=None,
    help="URL of the LDAP server",
)
parser.add_argument(
    "--outdir",
    type=str,
    action="store",
    default="",
    help="Directory where the history list files should be stored",
)
parser.add_argument(
    "--all-users",
    action="store_true",
    default=False,
    help="Process histories of all users, default only users not in LDAP",
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

key = os.environ.get('API_KEY', args.key)
galaxy_instance = GalaxyInstance(url=args.url, key=key)

ldap_conn = Connection(args.ldap_url, auto_bind=True)
base_dn = "ou=people,dc=ufz,dc=de"
ldap_conn.search(base_dn, "(objectClass=*)", SUBTREE, attributes=["uid", "cn", "mail"])
ldap_uids = set()
for entry in ldap_conn.entries:
    ldap_uids.add(entry.uid.value)
ldap_conn.unbind()
logger.info(f"Found {len(ldap_uids)} users in LDAP")

user_client = UserClient(galaxy_instance=galaxy_instance)
users = user_client.get_users()

user_by_id = {}
histories_by_user_id = {}
for user in users:
    uid = user["id"]
    username = user.get("username")
    email = user["email"]

    if not args.all_users and username in ldap_uids:
        logger.debug(f"Still present {username} {email} {uid}")
        continue
    logger.info(f"Consider {username} {email} {uid}")

    user_by_id[uid] = user
    histories_by_user_id[uid] = []
logger.info(f"Total {len(user_by_id)}/{len(users)} Galaxy users to delete")

size_left = 0
n_left = 0
size_present = 0
n_present = 0

history_client = HistoryClient(galaxy_instance)
offset = 1
while True:
    histories = history_client.get_histories(
        all=True, limit=USER_BATCH_SIZE, offset=offset, keys=["id", "user_id", "size"]
    )
    if not histories:
        break
    offset += USER_BATCH_SIZE

    for history in histories:
        user_id = history["user_id"]
        size = history["size"]
        if user_id not in user_by_id:
            size_present += size
            n_present += 1
            continue
        size_left += size
        n_left += 1
        histories_by_user_id[user_id].append(history)

if n_left:
    print(
        f"considered users: {round(size_left / (1024 ** 3))} GB in {n_left} histories"
    )
if n_present:
    print(
        f"ignored users: {round(size_present / (1024 ** 3))} GB in {n_present} histories"
    )

for user_id in user_by_id:
    username = user_by_id[user_id]["username"]
    with open(os.path.join(args.outdir, f"{username}.histories"), "a") as hf:
        for history_details in histories_by_user_id[user_id]:
            hf.write(f"{history_details['id']}\n")

for user_id in user_by_id:
    user_by_id[user_id]["size"] = 0
    for history_details in histories_by_user_id[user_id]:
        user_by_id[user_id]["size"] += history_details["size"]
for uid, user in sorted(user_by_id.items(), key=lambda d: d[1]["size"]):
    print(
        f"{user['username']} {len(histories_by_user_id[uid])} histories {user['size'] / (1024**3)} GB"
    )
