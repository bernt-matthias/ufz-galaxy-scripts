import argparse
import logging
import os
import subprocess

from bioblend.galaxy import GalaxyInstance
from ldap3 import Connection, SUBTREE

parser = argparse.ArgumentParser(
    description="List or remove user import libraries of users deleted users"
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
    "-log",
    "--loglevel",
    choices=["debug", "info", "warning", "error"],
    default="warning",
    help="Provide logging level. Example --loglevel debug, default=warning",
)
args = parser.parse_args()

logging.getLogger().setLevel(args.loglevel.upper())
logger = logging.getLogger(__name__)
# Set the log level for your logger to the desired level (e.g., INFO)
logger.setLevel(args.loglevel.upper())

# Create a handler for logging output (e.g., console handler)
handler = logging.StreamHandler()
logger.addHandler(handler)

# Add a formatter to the handler (optional)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)

key = os.environ.get('GALAXY_API_KEY', args.key)
gi = GalaxyInstance(url=args.url, key=key)

ldap_conn = Connection(args.ldap_url, auto_bind=True)
base_dn = "ou=people,dc=ufz,dc=de"
ldap_conn.search(base_dn, "(objectClass=*)", SUBTREE, attributes=["uid", "cn", "mail"])
ldap_users = dict()
for entry in ldap_conn.entries:
    ldap_users[entry.uid.value] = entry.cn.value
ldap_conn.unbind()
logger.info(f"Found {len(ldap_users)} users in LDAP")

config = gi.config.get_config()
user_library_import_dir = config.get("user_library_import_dir")
if not user_library_import_dir:
    logging.error("no user import directory defined")
    exit(1)

uil = gi.libraries.get_libraries(name = "user_data")
if len(uil) == 0:
    uil = gi.libraries.create_library(
        name="user_data",
        description="user libraries",
        synopsis="User libraries for importing from User library import directory"
    )
    logging.info("Created user import library user_data")
elif len(uil) == 1:
    uil = uil[0]
else:
    logging.error("more than one user import library existing")
    exit(1)
uil_id = uil["id"]
uil_root_folder_id = uil["root_folder_id"]

roles = {}
for r in gi.roles.get_roles():
    roles[r["name"]] = r["id"]

# create library import folders in the user import library
# - skip users with empty common name (deleted users)
# - skip sonkurs and songalax
users = gi.users.get_users()
for user in users:
    # logging.debug(f"{user=}")
    userid = user["id"]
    username = user["username"]
    email = user["email"]
    
    common_name = ldap_users.get(username)
    if not common_name:
        logging.error(f"User {username} absent in LDAP")
        continue
    if username.startswith("sonkurs") or username == "songalax":
        continue

    # create directory
    import_dir = os.path.join(user_library_import_dir, email)
    if import_dir.startswith("/gpfs"):
        import_dir = import_dir[6:]
    if not os.path.exists(import_dir):
        os.mkdir(import_dir)
        proc = subprocess.run(["setfacl", "-R", "-m", "u:songalax:rwX", "-m", "d:u:songalax:rwX", import_dir])
        proc.check_returncode()
        proc = subprocess.run(["setfacl", "-R", "-m", "u:{username}:rwX", "-m", "d:u:{username}:rwX", import_dir])
        proc.check_returncode()
        proc = subprocess.run(["setfacl", "-R", "-m", "m::rwx", "-m", "d:m::rwx", import_dir])
        proc.check_returncode()
    else:
        proc = subprocess.run(["sudo", "/global/apps/galaxy/scripts/external_chown_script.py", import_dir, "songalax", "eve_galaxy"])
        proc.check_returncode()
        proc = subprocess.run(["find", import_dir, "-type", "f", "-mtime", "+60", "-delete"])
        proc.check_returncode()

    # create library folder for the user
    uif = gi.libraries.get_folders(uil_id, name=f"/{username}")
    if len(uif) == 0:
        uif = gi.folders.create_folder(uil_root_folder_id, name=username, description=common_name)
        logging.info(f"Created new library folder for {username}")
    elif len(uif) == 1:
        uif = uif[0]
    else:
        logging.error(f"Found more than one library import folder for uname {username}")
        for f in uif[1:]:
            gi.folders.delete_folder(f["id"])
        uif = uif[0]
    
    # set permissions
    user_role_id = roles[email]
    gi.folders.set_permissions(
        uif["id"], add_ids=[user_role_id], manage_ids=[user_role_id], modify_ids=[user_role_id]
    )


