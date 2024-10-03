import utils
import logging
import os
import sys
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# print(os.listdir('../input'))
# os.listdir(clips_path)

# utils.upload_to_gcs("poodle-0324", 
#                     "autologger-0927957577",
                    
#                       )


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
            auth_url, _ = flow.authorization_url(prompt='consent')
            creds = flow.run_local_server(port=8080) # THIS IS BROKE
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


build_google_drive_client()