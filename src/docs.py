import os.path

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload


# Scopes for both read and write access to Google Docs
SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive.file",
]

# https://docs.google.com/document/d/1sZ-18GC1Kl5S3zPQgt9ek3xDb465rPdAmOmKDh5iqZQ
doc_id = "1sZ-18GC1Kl5S3zPQgt9ek3xDb465rPdAmOmKDh5iqZQ"

docs_client = None
drive_client = None  # used for image upload


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
    global docs_client
    """Retrieve the length of the document."""
    document = docs_client.documents().get(documentId=doc_id).execute()
    doc_content = document.get("body").get("content")
    end_index = doc_content[-1].get("endIndex", 1)  # Default to 1 if not found
    return end_index


# returns a tuple of the insert request with follow-up formatting request
# (API doesn't support formatting text while you insert  🤷‍♀️)
def build_text_request(friction_level, text):
    text = "\n" + text + "\n"
    global docs_client
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


# source:
# https://developers.google.com/docs/api/how-tos/images#python
def build_image_request(imgpath):
    global drive_client
    # step 1 - upload image to google drive via API
    file_metadata = {"name": os.path.basename(imgpath)}
    media = MediaFileUpload(imgpath, mimetype="image/png")
    file = (
        drive_client.files()
        .create(body=file_metadata, media_body=media, fields="id")
        .execute()
    )
    image_id = file.get("id")
    print("✅ Uploaded file to Google Drive: {}".format(image_id))

    # Make the screenshot public (⚠️) - note, docs API needs a public link
    # https://developers.google.com/docs/api/how-tos/images#python <-- see disclaimer
    permission = {
        "type": "anyone",
        "role": "reader",
    }
    drive_client.permissions().create(fileId=image_id, body=permission).execute()

    # step 2 - build request to insert image into google doc

    eod = get_document_length(doc_id) - 1

    drivepath = "https://drive.google.com/uc?id={}".format(image_id)
    r = {"insertInlineImage": {"location": {"index": eod}, "uri": drivepath}}

    return r


def main():
    global docs_client
    global drive_client
    # -------- AUTH ----------------------------------
    # TLDR: download a credentials.json, let the code create token.json w/ proper scopes
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    # NOTE - Creds apply to BOTH the docs and drive APIs
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
    # create clients
    try:
        docs_client = build("docs", "v1", credentials=creds)
        drive_client = build("drive", "v3", credentials=creds)

        # verify we have access to the doc in question
        document = docs_client.documents().get(documentId=doc_id).execute()
        print(f"The title of the document is: {document.get('title')}")

        reqs = []
        # add green
        reqs += build_text_request("GREEN", " This is positive feedback")
        reqs += build_text_request("ORANGE", "This is critical feedback")
        reqs += build_text_request("RED", "This is a blocker")

        print("\nInserting local image...")
        img_path = "../images/term.png"
        reqs += [build_image_request(img_path)]

        # Execute update
        docs_client.documents().batchUpdate(
            documentId=doc_id,
            body={"requests": reqs},
        ).execute()
        print("✅ Successfully updated document")

    except Exception as err:
        print("⚠️ Error: {}".format(err))


if __name__ == "__main__":
    main()
