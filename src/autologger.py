from google.cloud import storage
from moviepy.editor import VideoFileClip
from vertexai.generative_models import GenerativeModel, Part
from video_utils import (
    chunk_video_and_grab_screenshots,
    upload_to_gcs,
    write_clips_to_json,
)
from google_docs_utils import (
    build_insert_text_request,
    build_insert_image_request,
    build_insert_header_request,
)
import json
import os
import time
import vertexai
from clip import Clip

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# GOOGLE CLOUD APIS CONFIG
project_id = "cpet-sandbox"
bucket_name = "cpet-autologger"
model_name = "gemini-1.5-flash-001"
fl_description = "You are an automated Friction Log generator. Your job is to take a recording or transcript, and summarize the developer's journey on a specific task: each step, with the highs and lows (sentiment) of their experience."
# GOOGLE DRIVE / DOCS API CONFIG
docs_client = None
drive_client = None
SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive.file",
]

# ⭐ CONFIGURE THESE FOR EACH FL TOPIC
doc_id = "14s-sKUJLlXYcn6RxFt5sDXrKnMbKejH0YivRHEFeuiA"
gcs_folder_prefix = "java-cloudrun-" + str(int(time.time()))


####### -------- GEMINI ON VERTEX HELPERS  ----------------- #######
# gets the full text transcript for a 1 minute video chunk
def get_transcript(video_gcs_path):
    global project_id
    global fl_description
    global model_name

    try:
        vertexai.init(project=project_id, location="us-central1")
        model = GenerativeModel(model_name=model_name)

        prompt = """
        Transcribe this one-minute video, word for word. Add punctuation to improve readability - avoid run on sentences. Return ONLY the exact transcript."""

        video_file = Part.from_uri(video_gcs_path, mime_type="video/mp4")
        contents = [video_file, prompt]
        response = model.generate_content(contents)
    except Exception as e:
        print(f"❌ Error getting transcript: {e}")
        return ""
    transcript = response.text
    transcript = transcript.strip()
    return transcript


# https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/image-understanding#send-images
def get_summary(transcript, screenshots_paths):
    global project_id
    global bucket_name
    global fl_description
    global model_name

    try:
        vertexai.init(project=project_id, location="us-central1")
        model = GenerativeModel(model_name=model_name)
        prompt_contents = []
        text_prompt = """
        {}
        YOUR TASK: Generate a 2-4 sentence summary of what this developer did, based on the transcript and accompanying screenshots. Be as detailed as possible. 
        
        RETURN A SUMMARY IN FIRST PERSON using the "We" pronoun, for example: "We tried to ... " 
        
        TRANSCRIPT: {}
        """.format(
            fl_description, transcript
        )
        prompt_contents.append(text_prompt)
        for sp in screenshots_paths:
            prompt_contents.append(Part.from_uri(sp, mime_type="image/jpeg"))
        response = model.generate_content(prompt_contents)
    except Exception as e:
        print(f"❌ Error getting summary: {e}")
        return []
    summary = response.text.strip()
    return response.text


def get_sentiment(transcript, screenshots_paths, summary):
    global project_id
    global fl_description
    global model_name

    try:
        vertexai.init(project=project_id, location="us-central1")
        model = GenerativeModel(model_name=model_name)
        prompt_contents = []
        text_prompt = """
        {}
        YOUR TASK: Given a video transcript, paragraph summary, and a selection of screenshots, evaluate the SENTIMENT of this video clip.  
        Return ONLY one of the following values: NEUTRAL, POSITIVE, SOMEWHAT_NEGATIVE, VERY_NEGATIVE. 
        
        TRANSCRIPT: {} 
        
        SUMMARY: {}
        """.format(
            fl_description, transcript, summary
        )
        prompt_contents.append(text_prompt)
        for sp in screenshots_paths:
            prompt_contents.append(Part.from_uri(sp, mime_type="image/jpeg"))
        response = model.generate_content(prompt_contents)
    except Exception as e:
        print(f"❌ Error getting sentiment: {e}")
        return []
    return response.text.strip()


####### ---------------- GOOGLE DOCS MAGIC  --------------------------------
def generate_friction_log(clips):
    # Init Google Drive / Docs Clients
    global docs_client
    global drive_client
    global doc_id
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    try:
        docs_client = build("docs", "v1", credentials=creds)
        drive_client = build("drive", "v3", credentials=creds)
        document = docs_client.documents().get(documentId=doc_id).execute()
        print(f"The title of the document is: {document.get('title')}")
    except Exception as e:
        print("❌ Error initializing Google Docs/Drive API client: {}".format(e))
        return

    # we'll do a batch update. reqs = all the Docs API requests:
    reqs = []

    # Insert summaries with screenshots
    reqs.append(
        build_insert_header_request(
            docs_client, doc_id, "Friction Log Draft - Generated by Autologger", 2
        )
    )
    reqs.append(build_insert_text_request(docs_client, doc_id, "\n", "NEUTRAL"))
    reqs = reqs[::-1]
    try:
        docs_client.documents().batchUpdate(
            documentId=doc_id,
            body={"requests": reqs},
        ).execute()
    except Exception as err:
        print("⚠️ Error writing to Google Docs: {}".format(err))

    for c in clips:
        reqs = []
        # Insert summary
        reqs.append(
            build_insert_text_request(docs_client, doc_id, c.summary, c.sentiment)
        )
        # Insert screenshots
        for sp in sorted(c.screenshots_paths):
            reqs.append(
                build_insert_image_request(drive_client, docs_client, doc_id, sp)
            )
        reqs = reqs[::-1]
        try:
            docs_client.documents().batchUpdate(
                documentId=doc_id,
                body={"requests": reqs},
            ).execute()
        except Exception as err:
            print("⚠️ Error writing to Google Docs: {}".format(err))

    reqs = []
    # Insert raw transcript at the end of the doc
    reqs.append(
        build_insert_header_request(docs_client, doc_id, "Appendix: Raw Transcript", 3)
    )
    for c in clips:
        reqs.append(
            build_insert_text_request(docs_client, doc_id, c.transcript, "NEUTRAL")
        )
    # reverse the order of reqs
    reqs = reqs[::-1]
    try:
        docs_client.documents().batchUpdate(
            documentId=doc_id,
            body={"requests": reqs},
        ).execute()
    except Exception as err:
        print("⚠️ Error writing to Google Docs: {}".format(err))
    print("✅ Successfully updated Google Doc")
    return


def autologger(video_path):

    print(
        """
             _        _                             
            | |      | |                            
  __ _ _   _| |_ ___ | | ___   __ _  __ _  ___ _ __ 
 / _` | | | | __/ _ \| |/ _ \ / _` |/ _` |/ _ \ '__|
| (_| | |_| | || (_) | | (_) | (_| | (_| |  __/ |   
 \__,_|\__,_|\__\___/|_|\___/ \__, |\__, |\___|_|   
                               __/ | __/ |          
                              |___/ |___/           
    """
    )
    print(
        "\n📠 Hello. I am an AI-powered friction log generator. I will create a friction log draft from: {}\n".format(
            video_path
        )
    )
    global bucket_name
    global gcs_folder_prefix
    global project_id
    chunk_video_and_grab_screenshots(video_path)
    clips = []

    subdirs = os.listdir("./out")
    # sort by chunk_number, so chunk_9, chunk_10, chunk_11 ...
    ordered_dirs = sorted(subdirs, key=lambda x: int(x.split("_")[1]))
    print("Processing clips: {}".format(ordered_dirs))
    for subdir in ordered_dirs:
        print("\n 🎞️ Processing clip: {}".format(subdir))
        c = Clip(None, None, None, None, None)
        c.video_gcs_path, c.screenshots_paths = upload_to_gcs(
            project_id, bucket_name, gcs_folder_prefix, subdir
        )
        c.transcript = get_transcript(c.video_gcs_path)
        c.summary = get_summary(c.transcript, c.screenshots_paths)
        c.sentiment = get_sentiment(c.transcript, c.screenshots_paths, c.summary)
        clips.append(c)

    # save intermediate state to JSON (for testing + debugging)
    write_clips_to_json(clips)

    print("🤖 Done Video and AI processing. Ready to write to Google Docs.")

    with open("clips.json") as f:
        clips = json.load(f)
        clips = [
            Clip(
                c["video_gcs_path"],
                c["screenshots_paths"],
                c["transcript"],
                c["summary"],
                c["sentiment"],
            )
            for c in clips
        ]
    generate_friction_log(clips)


if __name__ == "__main__":
    autologger("../test_recordings/java_cloudrun.mp4")
