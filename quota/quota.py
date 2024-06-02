"""
Script to automatize quota management for single user quotas

- each user can have an additional quota with an expiration date
- the expiration date is stored in the quota description
- new quotas can be added (or updated) by adding entries to a file
  "#email\tamount\texpiration dd.mm.yyy"
- expired quotas are deleted
"""

import argparse
import logging
import os
import smtplib
import sys
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from bioblend import (
    ConnectionError,
    galaxy,
)


# TODO replace by Galaxy notification?
def send_notification(receiver_email: str, subject: str, message: str) -> bool:
    sender_email = "m.bernt@ufz.de"

    # Create a MIMEText object for the email content
    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg["Subject"] = subject
    msg.attach(MIMEText(message, "plain"))

    # Connect to the SMTP server
    try:
        server = smtplib.SMTP("localhost")
    except ConnectionRefusedError:
        logger.error(f"Could not send mail: could not connect to {smtp_server}")
        return False

    # Send the email
    try:
        server.sendmail(sender_email, receiver_email, msg.as_string())
        logger.debug("Email sent successfully!")
    except Exception as e:
        logger.error(
            f"Notification email could not be sent to {receiver_email}. Error:", str(e)
        )
        return False

    # Close the SMTP server connection
    server.quit()
    return True


parser = argparse.ArgumentParser(description="List / install containers")
parser.add_argument(
    "--url", type=str, action="store", required=True, default=None, help="Galaxy URL"
)
parser.add_argument(
    "--key", type=str, action="store", required=True, default=None, help="API key"
)
parser.add_argument(
    "--file",
    type=str,
    action="store",
    required=False,
    default=None,
    help="quota update file: tab separated: email, amount, time",
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

gi = galaxy.GalaxyInstance(url=args.url, key=args.key)

try:
    version = gi.config.get_version()
    whoami = gi.config.whoami()
    logger.debug(f"Connected as {whoami['username']} to {args.url} ({version})")
except ConnectionError:
    sys.exit(f"Could not connect to {args.url}")

users = gi.users.get_users()

# get mapping from email to users
mail2user = {user["email"]: user for user in users}

# get mapping from email to quotas
# and delete expired quotas
mail2quota = {}
for deleted in [False, True]:
    quotas = gi.quotas.get_quotas(deleted=deleted)
    for quota in quotas:
        quota = gi.quotas.show_quota(quota["id"], deleted=deleted)

        # skip default quota
        if len(quota["default"]) > 0:
            continue
        # only consider (single) user quotas
        if len(quota["users"]) != 1:
            continue

        email = quota["users"][0]["user"]["email"]
        # store deleted info in quota
        quota['deleted'] = deleted
        mail2quota[email] = quota

        if deleted:
            continue
        logger.debug(f"Checking expiration of {quota['name']} {quota['description']}")
        try:
            expires = datetime.strptime(quota["description"], "%d.%m.%Y")
        except ValueError:
            logger.error(
                f"quota {quota['name']}: description is not expiration date {quota['description']}"
            )
            continue

        if datetime.now() > expires:
            logger.error(f"Quota {quota['name']} ({quota['display_amount']}) expired")
            gi.quotas.delete_quota(quota["id"])
            send_notification(
                email,
                "UFZ Galaxy: quota expiration",
                f"Your additional Galaxy quota of {quota['display_amount']} expired."
            )
        if datetime.now() > expires - timedelta(days=30):
            send_notification(
                email,
                "UFZ Galaxy: quota expiration",
                f"Your additional Galaxy quota of {quota['display_amount']} will expire in {(expires - datetime.now()).days} days (on {quota['description']})."
            )
if not args.file or not os.path.exists(args.file):
    logger.debug(f"no such file: {args.file}")
    sys.exit(0)

with open(args.file) as fh:
    for line in fh:
        if line.startswith("#"):
            continue
        line = line.strip()
        if len(line) == 0:
            continue
        line = line.split()
        if len(line) != 3:
            sys.exit(f"misformatted line {line}")

        try:
            user = mail2user[line[0]]
        except KeyError:
            log.error(f"No such user: {line[0]}")

        amount = line[1]

        date = datetime.strptime(line[2], "%d.%m.%Y")

        # if there is already a quota for the user -> undelete and update it
        # otherwise create it
        if user["email"] in mail2quota:
            logger.error(f"Updating quota {user['username']}")

            if mail2quota[user["email"]]["deleted"]:
                gi.quotas.undelete_quota(mail2quota[user["email"]]["id"])

            gi.quotas.update_quota(
                quota_id=mail2quota[user["email"]]["id"],
                name=user["username"],
                description=line[2],
                # default='no',
                amount=amount,
                operation="+",
                in_users=[user["id"]],
            )
            send_notification(
                user['email'],
                "UFZ Galaxy: quota granted",
                f"Your additional Galaxy quota of {amount} with expiration date {line[2]} has been updated."
            )
        else:
            logger.debug(f"Creating quota {user['username']}")
            gi.quotas.create_quota(
                name=user["username"],
                description=line[2],
                amount=amount,
                operation="+",
                in_users=[user["id"]],
            )
            send_notification(
                user['email'],
                "UFZ Galaxy: quota granted",
                f"Your additional Galaxy quota of {amount} with expiration date {line[2]} has been added."
            )

with open(args.file, "w") as fh:
    fh.write("#email\tamount\texpiration dd.mm.yyy\n")
