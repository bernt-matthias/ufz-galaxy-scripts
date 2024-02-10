import argparse
import logging
import subprocess

from bioblend.galaxy import GalaxyInstance
from bioblend.galaxy.users import  UserClient
from bioblend.galaxy.histories import HistoryClient

def run_external_program(command):
    try:
        result = subprocess.run(
            command,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        exit_code = result.returncode
        stdout = result.stdout.decode('utf-8')
        stderr = result.stderr.decode('utf-8')
        return exit_code, stdout, stderr
    except subprocess.CalledProcessError as e:
        exit_code = e.returncode
        stderr = e.stderr.decode('utf-8')
        stdout = e.stdout.decode('utf-8')
        return exit_code, stdout, stderr

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

user_client = UserClient(galaxy_instance=galaxy_instance)
users = user_client.get_users()

history_client = HistoryClient(galaxy_instance)
histories = history_client.get_histories(all=True)

left_user_by_id = {}

for user in users:
    user_id = user['id']
    username= user['username']
    email = user['email']
    exit_code, uid, stderr = run_external_program(["id", "-u", username])
    try:
        uid = int(uid)
    except ValueError:
        uid = -1
    if not exit_code and uid >= 1000:
        print(f"still present {username} {email} {uid}")
        continue
    left_user_by_id[user_id] = user

print(f"{len(left_user_by_id)} users left")

left_histories_by_user_id = {}
size_left = 0
n_left = 0
size_present = 0
n_present = 0
for history in histories:
    history_details = galaxy_instance.histories.show_history(history['id'])
    user_id = history_details['user_id']
    size = history_details['size']
    if user_id not in left_user_by_id:
        size_present += size
        n_present += 1
        continue
    size_left += size
    n_left += size
    try:
        left_histories_by_user_id[user_id].append(history)
    except KeyError:
        left_histories_by_user_id[user_id] = [history]
        
print(f"left users: {size_left} in {n_left}")
print(f"present users: {size_present} in {n_present}")