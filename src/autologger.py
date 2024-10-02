import configparser
import imageio
import json
import logging
import os
import os.path
import sys
import time
import textwrap

from clip import Clip
from utils import make_topic_folders

from mdutils.mdutils import MdUtils
from mdutils.tools.Html import Html
from moviepy.editor import VideoFileClip

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from google.cloud import storage
import vertexai.preview
from vertexai.generative_models import GenerativeModel, Part


#  🎞️ VIDEO / SCREENSHOT HELPERS  🎞️
def write_clips_to_json(clips, filename="clips.json"):
    clips_dict = [clip.to_dict() for clip in clips]
    with open(filename, "w") as f:
        json.dump(clips_dict, f, indent=4)


# splits the input video into [interval]-second clips. grabs 2 screenshots per clip.
def split_video_and_grab_screenshots(video_path, clip_length, out_dir):
    logging.info(
        "🎥 Breaking your video into {}-second clips.".format(clip_length)
    )
    clip_length = int(clip_length)

    try:
        video = VideoFileClip(video_path)
        duration = video.duration
        start_time = 0
        clip_index = 0

        while start_time < duration:
            end_time = min(start_time + clip_length, duration)
            clip = video.subclip(start_time, end_time)
            clip_dir = f"{out_dir}/clip_{clip_index}"
            if not os.path.exists(clip_dir):
                os.makedirs(clip_dir)
            clip_file_name = f"{clip_dir}/video.mp4"
            clip.write_videofile(
                clip_file_name, codec="libx264", audio_codec="aac"
            )

            # Capture and save screenshots every 30 seconds within the clip
            for screenshot_time in range(
                0, min(clip_length, int(end_time - start_time)), 30
            ):
                screenshot = clip.get_frame(screenshot_time)
                screenshot_file_name = (
                    f"{clip_dir}/screenshot_{screenshot_time//30}.jpg"
                )
                imageio.imwrite(screenshot_file_name, screenshot)
            start_time += clip_length
            clip_index += 1
    except Exception as e:
        logging.error(f"❌ Error breaking video into clips: {e}")
        sys.exit(1)
    logging.info(
        "✂️ Successfully split video into clips + grabbed screenshots. Ready for Gemini processing."
    )


def build_google_drive_client():
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
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", scopes
            )
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    try:
        drive_client = build("drive", "v3", credentials=creds)
    except Exception as e:
        print("❌ Error initializing Google Drive API client: {}".format(e))
        sys.exit(1)
    return drive_client


# upload both screenshots and video to Google Cloud Storage bucket (for Vertex AI Gemini inference)
def upload_to_drive_gcs(
    project_id, bucket_name, c: Clip, folder_prefix, subdir
):
    formatted_video_gcs_path = ""
    local_directory = "./clips"
    storage_client = storage.Client(project=project_id)
    bucket = storage_client.bucket(bucket_name)
    target_directory = "{}/{}".format(folder_prefix, subdir)

    drive_client = build_google_drive_client()
    video_gcs_path = ""
    ss_gcs_paths = []
    ss_drive_paths = []

    try:
        for screenshot in os.listdir(f"./clips/{subdir}"):
            # SCREENSHOTS --> GCS and DRIVE
            if screenshot.endswith(".jpg"):
                sp = f"{target_directory}/screenshots/{screenshot}"
                ss_gcs_paths.append("gs://{}/{}".format(bucket_name, sp))
                blob = bucket.blob(sp)
                local_path = f"{local_directory}/{subdir}/{screenshot}"
                logging.debug("🖼️ Uploading screenshot to GCS: " + sp)
                blob.upload_from_filename(local_path)
                logging.debug(
                    f"⬆️ Uploaded {screenshot} to Google Cloud Storage, bucket: {bucket_name}, directory: {target_directory}"
                )
                file_metadata = {
                    "name": c.topic
                    + "_"
                    + str(c.clip_number)
                    + "_"
                    + os.path.basename(local_path)
                }
                logging.debug(
                    "💿 Uploading screenshot to Google Drive: {}".format(
                        file_metadata
                    )
                )

                media = MediaFileUpload(local_path, mimetype="image/jpg")
                file = (
                    drive_client.files()
                    .create(body=file_metadata, media_body=media, fields="id")
                    .execute()
                )
                image_id = file.get("id")
                print(
                    "✅ Uploaded screenshot to Google Drive: {}".format(
                        image_id
                    )
                )
                ss_drive_paths.append(
                    "https://drive.google.com/uc?id=" + image_id
                )

                # Make the screenshot public (⚠️) - note, Google docs needs a public link
                # https://developers.google.com/docs/api/how-tos/images#python <-- see disclaimer
                permission = {
                    "type": "anyone",
                    "role": "reader",
                }
                drive_client.permissions().create(
                    fileId=image_id, body=permission
                ).execute()

            # VIDEO --> GCS
            else:
                video_gcs_path = f"{target_directory}/video.mp4"
                blob = bucket.blob(video_gcs_path)
                blob.upload_from_filename(f"./clips/{subdir}/video.mp4")
                video_gcs_path = "gs://{}/{}".format(
                    bucket_name, video_gcs_path
                )
                logging.debug("🎥 Uploaded video to GCS: " + video_gcs_path)

    except Exception as e:
        logging.error(f"❌ Error on upload: {e}")
        return ""
    return video_gcs_path, ss_gcs_paths, ss_drive_paths


def gemini_process(c: Clip, project_id, model_name, sys_inst):
    print("\n\n 🚀 Processing with Gemini. c: {}".format(c))
    try:
        vertexai.init(project=project_id, location="us-central1")
        model = GenerativeModel(model_name=model_name)

        # TRANSCRIPTION
        print("\n TRANSCRIPTION....")
        prompt = """
        Transcribe this video, word for word. Add punctuation to improve readability - avoid run on sentences. Return ONLY the exact transcript."""
        video_file = Part.from_uri(c.video_gcs_path, mime_type="video/mp4")
        print(
            "video gcs path: {}, video file: {}".format(
                c.video_gcs_path, video_file
            )
        )
        contents = [video_file, prompt]
        response = model.generate_content(contents)
        transcript = response.text
        transcript = transcript.strip()
        logging.debug("🎤 Raw Transcript: " + transcript)

        # SUMMARIZATION WITH SENTIMENT
        print("\n SUMMARIZATION WITH SENTIMENT ANALYSIS....")
        model = model = GenerativeModel(
            model_name=model_name,
            system_instruction=[
                "You are a friction log generator. A friction log is a written record of a developer's experience. You will be given a video, the video's transcript, and some screenshots. YOUR TASK: summarize the contents of the video, using the transcript and screenshots. Use collective first person, using we pronouns. Be as detailed as possible - up to 4-5 sentences per summary. If you see hyperlinks or code, include them in your summary - not as part of the 5 sentence count. IMPORTANT: Tag sentiment as follows: ✅ Positive (This went well). ⚠️ Some developer friction (This was challenging). ❌ Significant developer friction (This was a blocker). If the summary is neutral sentiment, do not use any emoji. Always put the emoji at the BEGINNING of the summary. It should be the first character.",
                sys_inst,
            ],
        )
        prompt_contents = [
            "Transcript: " + transcript,
            Part.from_uri(c.video_gcs_path, mime_type="video/mp4"),
        ]
        for sp in c.ss_gcs_paths:
            prompt_contents.append(Part.from_uri(sp, mime_type="image/jpeg"))
        response = model.generate_content(prompt_contents)
        summ = response.text
        summ = summ.strip()
        print("Got summary: ", summ)
        return transcript, summ
    except Exception as e:
        print(f"❌ Error processing with Gemini: {e}")
        return ""


def autologger():
    logging.basicConfig(
        level=logging.DEBUG, format="%(levelname)s:%(name)s:%(message)s"
    )
    logging.info(
        r"""
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
    config = configparser.ConfigParser()
    configFilePath = "config.ini"
    config.read(configFilePath)

    # base path for videos (defaults to ../input)
    source_folder = config["autologger"]["video_path"]

    topic_list = make_topic_folders(source_folder)

    # TODO: loop and execute all processing steps for all video files (see GH issue #15)
    # (for now; just do the first one)
    video_path = os.path.join(source_folder, f"{topic_list[0]}.mp4").strip()
    topic = topic_list[0]

    interval = config["autologger"]["summary_interval_secs"]
    model = config["autologger"]["vertexai_model"]
    sys_inst = config["autologger"]["system_instructions"]
    project_id = config["autologger"]["gcp_project_id"]
    bucket_name = config["autologger"]["gcs_bucket_name"]

    clips_path = os.path.join("./clips", topic)  # local storage for clips split from source video

    logging.info(
        textwrap.dedent(
            f"""\n
            ✅ Config loaded. \n
            topic: {topic}\n
            video path: {video_path}\n
            interval: {interval}\n
            model: {model}\n
            system instructions: {sys_inst}\n
            gcp project id:{project_id}\n
            gcs_bucket_name:{bucket_name}
            """
        )
    )
    fl = MdUtils(file_name="out/" + topic, title=topic)

    # break the input file into clips
    # (if there are already clips in the clips dir, skip this step)
    if os.listdir(os.path.join(clips_path)):
        logging.info(
            f"Already have clips in folder: {clips_path};"
            + f" to re-generate clips, delete {clips_path}"
            )
    else:
        split_video_and_grab_screenshots(video_path, interval, clips_path)

    clips = []
    subdirs = os.listdir(clips_path)
    ordered_dirs = sorted(subdirs, key=lambda x: int(x.split("_")[1]))
    print(
        "🚧 Building your friction log, one video clip at a time: {}".format(
            ordered_dirs
        )
    )
    subdirs = os.listdir(clips_path)
    ordered_dirs = sorted(subdirs, key=lambda x: int(x.split("_")[1]))
    print("🚧 Building your friction log: {}".format(ordered_dirs))
    for i, subdir in enumerate(ordered_dirs):
        print("\n 🎞️ Processing clip: {}".format(subdir))
        c = Clip(
            topic=topic,
            clip_number=i,
            video_gcs_path=None,
            ss_gcs_paths=None,
            ss_drive_paths=None,
            transcript=None,
            summary=None,
        )
        logging.info(
            "\nUploading video and screenshots to GCS and Google Drive..."
        )
        c.video_gcs_path, c.ss_gcs_paths, c.ss_drive_paths = (
            upload_to_drive_gcs(
                project_id,
                bucket_name,
                c,
                topic + str(int(time.time())),
                subdir,
            )
        )

        logging.info(
            "\nGenerating transcript and summary/sentiment with Gemini..."
        )
        c.transcript, c.summary = gemini_process(
            c, project_id, model, sys_inst
        )
        clips.append(c)
        write_clips_to_json(clips)
        logging.info(
            "📝 Writing summary and screenshots to Friction Log markdown..."
        )
        fl.new_paragraph(c.summary)
        for drive_path in c.ss_drive_paths:
            fl.new_paragraph(
                Html.image(
                    path=drive_path,
                    size="600",
                )
            )
    logging.info("Writing final friction log to local markdown...")
    fl.create_md_file()

    logging.info(
        "🏁 Autologger complete. Output file at: {}".format("out/" + topic)
    )


if __name__ == "__main__":
    autologger()
