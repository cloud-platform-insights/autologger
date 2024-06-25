import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Scopes for both read and write access to Google Docs
SCOPES = ["https://www.googleapis.com/auth/documents"]

# https://docs.google.com/document/d/1sZ-18GC1Kl5S3zPQgt9ek3xDb465rPdAmOmKDh5iqZQ
doc_id = "1sZ-18GC1Kl5S3zPQgt9ek3xDb465rPdAmOmKDh5iqZQ"

service = None


def hex_to_rgb(hex_color):
    """Converts hex color string to an RGB dictionary."""
    hex_color = hex_color.lstrip("#")
    lv = len(hex_color)
    return {
        "red": int(hex_color[0:2], 16) / 255.0,
        "green": int(hex_color[2:4], 16) / 255.0,
        "blue": int(hex_color[4:], 16) / 255.0,
    }


def get_document_length(doc_id):
    global service
    """Retrieve the length of the document."""
    document = service.documents().get(documentId=doc_id).execute()
    doc_content = document.get("body").get("content")
    end_index = doc_content[-1].get("endIndex", 1)  # Default to 1 if not found
    return end_index


# returns a tuple of the insert request with follow-up formatting request
# (API doesn't support formatting text while you insert  🤷‍♀️)
def build_request(friction_level, text):
    text = "\n" + text + "\n"
    global service
    eod = get_document_length(doc_id) - 1

    highlight_color = "#FFFFFF"
    if friction_level == "GREEN":
        highlight_color = "#D7FED4"
    elif friction_level == "ORANGE":
        highlight_color = "#FFD699"
    elif friction_level == "RED":
        highlight_color = "#FFD4D4"
    rgb_color = hex_to_rgb(highlight_color)

    insert_request = {
        "insertText": {
            "location": {
                "index": eod,
            },
            "text": text,
        }
    }

    format_request = {
        "updateTextStyle": {
            "range": {
                "startIndex": eod,
                "endIndex": eod + len(text),
            },
            "textStyle": {"backgroundColor": {"color": {"rgbColor": rgb_color}}},
            "fields": "backgroundColor",
        }
    }

    return [insert_request, format_request]


def main():
    global service
    # -------- AUTH ----------------------------------
    # TLDR: download a credentials.json, let the code create token.json w/ proper scopes
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    try:
        service = build("docs", "v1", credentials=creds)

        # verify we have access to the doc in question
        document = service.documents().get(documentId=doc_id).execute()
        print(f"The title of the document is: {document.get('title')}")

        reqs = []
        # add green
        reqs += build_request("GREEN", " This is positive feedback")
        reqs += build_request("ORANGE", "This is critical feedback")
        reqs += build_request("RED", "This is a blocker")

        # Execute update
        result = (
            service.documents()
            .batchUpdate(
                documentId=doc_id,
                body={"requests": reqs},
            )
            .execute()
        )

        print("The result of the batch update is: {0}".format(result))

    except HttpError as err:
        print(err)


if __name__ == "__main__":
    main()
