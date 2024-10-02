import os
import sys
import logging

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


def make_topic_folders(source_folder: str) -> list[str]:
    topic_list = []

    video_files = [
        item
        for item in os.listdir(source_folder)
        if os.path.isfile(os.path.join(source_folder, item))
        and item.endswith(".mp4")
    ]

    for file in video_files:
        topic_list.append(file.split(".")[0])

    # create output directories if they don't exist
    directories = ["./clips", "./out"]

    for topic in topic_list:
        for directory in directories:
            topic_directory = os.path.join(directory, topic)
            os.makedirs(topic_directory, exist_ok=True)

    return topic_list


def build_google_drive_client() -> None:
    creds = None
    scopes = [
        "https://www.googleapis.com/auth/drive.file",
    ]
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", scopes)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists("./credentials.json"):
                logging.fatal(
                    "Error - File not found: credentials.json (see README.md)"
                )
                sys.exit(1)
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", scopes
            )
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    try:
        drive_client = build("drive", "v3", credentials=creds)
    except Exception as e:
        logging.fatal(
            "❌ Error initializing Google Drive API client: {}".format(e)
        )
        sys.exit(1)
    return drive_client
