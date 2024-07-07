import os.path
import os
from googleapiclient.http import MediaFileUpload
from google.cloud import storage


##### ----------------- HELPER FUNCTIONS ----------------- #####
def hex_to_rgb(hex_color):
    """Converts hex color string to an RGB dictionary."""
    hex_color = hex_color.lstrip("#")
    lv = len(hex_color)
    return {
        "red": int(hex_color[0:2], 16) / 255.0,
        "green": int(hex_color[2:4], 16) / 255.0,
        "blue": int(hex_color[4:], 16) / 255.0,
    }


def get_document_length(docs_client, doc_id):
    """Retrieve the length of the document."""
    document = docs_client.documents().get(documentId=doc_id).execute()
    doc_content = document.get("body").get("content")
    end_index = doc_content[-1].get("endIndex", 1)  # Default to 1 if not found
    return end_index


# returns a tuple of the insert request with follow-up formatting request
# (API doesn't support formatting text while you insert  🤷‍♀️)
def build_insert_text_request(docs_client, doc_id, text, friction_level):
    text = "\n" + text + "\n"
    eod = get_document_length(docs_client, doc_id) - 1

    highlight_color = "#FFFFFF"
    if friction_level == "POSITIVE":
        highlight_color = "#D7FED4"
    elif friction_level == "SOMEWHAT_NEGATIVE":
        highlight_color = "#FFD699"
    elif friction_level == "VERY_NEGATIVE":
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


# Insert screenshots into the document
# source:
# https://developers.google.com/docs/api/how-tos/images#python
def build_insert_image_request(drive_client, docs_client, doc_id, gcs_url):
    # download image via Google Cloud Storage client
    path_parts = gcs_url[len("gs://") :].split("/", 1)
    bucket_name = path_parts[0]
    blob_name = path_parts[1]
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    # create local path for the image
    # replace all slashes in blob_name with underscores
    local_path = f"./gcs_downloads/{blob_name.replace('/', '_')}"
    blob.download_to_filename(local_path)
    print(f"GCS Screenshot downloaded to {local_path}")

    # upload local image to Google Drive
    file_metadata = {"name": os.path.basename(local_path)}
    media = MediaFileUpload(local_path, mimetype="image/jpg")
    file = (
        drive_client.files()
        .create(body=file_metadata, media_body=media, fields="id")
        .execute()
    )
    image_id = file.get("id")
    print("✅ Uploaded screenshot to Google Drive: {}".format(image_id))

    # Make the screenshot public (⚠️) - note, docs API needs a public link
    # https://developers.google.com/docs/api/how-tos/images#python <-- see disclaimer
    permission = {
        "type": "anyone",
        "role": "reader",
    }
    drive_client.permissions().create(fileId=image_id, body=permission).execute()

    eod = get_document_length(docs_client, doc_id) - 1

    drivepath = "https://drive.google.com/uc?id={}".format(image_id)
    r = {"insertInlineImage": {"location": {"index": eod}, "uri": drivepath}}

    return r
