"""
Add new encryption keys to a vault config
and allow to remove old one (by limiting the maximum number)
"""

import argparse
import yaml
from cryptography.fernet import Fernet

parser = argparse.ArgumentParser()
parser.add_argument(
    "--config",
    metavar="CONFIG",
    type=str,
    default=None,
    required=True,
    help="vault config file",
)
# parser.add_argument(
#     "--maxkeys", action="store", type=int, default=None, help="maximum number of keys"
# )
args = parser.parse_args()

config = args.config
maxkeys = args.maxkeys

with open(config) as f:
    vc = yaml.safe_load(f)

new_key = Fernet.generate_key().decode("utf-8")

if vc.get("encryption_keys") is None:
    print('loaded 0 keys')
    vc["encryption_keys"] = [new_key]
else:
    print(f'loaded {len(vc["encryption_keys"])} keys')
    vc["encryption_keys"] = [new_key] + vc["encryption_keys"]

# if maxkeys and len(vc["encryption_keys"]) > maxkeys:
#     vc["encryption_keys"] = vc.encryption_keys[:-1]

print(f'writing {len(vc["encryption_keys"])} keys')
with open(config, "w") as f:
    yaml.dump(vc, f, sort_keys=False)
