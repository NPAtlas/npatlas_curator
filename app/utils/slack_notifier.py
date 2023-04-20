from os import getenv

import requests

WEBHOOK_URL = getenv("SLACK_WEBHOOK_URL")


def send_message(message):
    requests.post(WEBHOOK_URL, json={"text": message})


def send_dataset_complete(dataset):
    message = "Dataset {0} ({1}) was completed by {2}!".format(
        dataset.id, dataset.instructions, dataset.curator.full_name
    )
    send_message(message)
