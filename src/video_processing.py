"""
📠 AUTOLOGGER STEPS: 
- Break down Meet recording into 1 minute clips, and grab screenshots every 15 seconds (ie. 4 screenshots per 1-minute clip) --> upload video chunks and screenshots to GCS for Gemini processing 
(We are NOT using the Meet generated transcript, because it only has timestamps every 5 mins - hard to match to exact screenshots.)

- Use Gemini to process all clips:
        - Transcribe audio 
        - Generate a 2-3 sentence summary
        - Given transcription, summary, and all 10 screenshots, evaluate sentiment of the clip (NEUTRAL, POSITIVE, SOMEWHAT_NEGATIVE, VERY_NEGATIVE) 

- Then, connect to the output Google Doc (friction log) and: 
    - In sequence, write all color-coded summaries and screenshots: this is the scaffolding of the friction log. 
    - Write entire transcript to the end of the doc (As an appendix) 

From here, we'd expect the user to: 
    - Review the output, make corrections (eg. mis-colored sentiment) 
    - Delete unneeded or duplicate screenshots 
    - Add their own screenshots, code, links to docs used 
    - Add their own context to the findings 
    - Fill out the summary at the top of the doc 
    - File bugs for orange/red items 
"""

from google.cloud import storage
from moviepy.editor import VideoFileClip
from vertexai.generative_models import GenerativeModel, Part

import imageio
import json
import os
import time
import vertexai


class Clip:
    def __init__(
        self,
        local_path,
        video_gcs_path,
        transcript,
        screenshots_paths,
        summary,
        sentiment,
    ):
        self.local_path = local_path
        self.video_gcs_path = video_gcs_path
        self.transcript = transcript
        self.screenshots_path = screenshots_paths
        self.summary = summary
        self.sentiment = sentiment

    def __str__(self):
        return """ 
        \n
        🎞️ Clip: {} 
                Video GCS path: {}
                # Screenshots paths: {}
                Transcript length: {}  
                Summary: {}
                Sentiment: {}
        \n
        """.format(
            self.local_path,
            self.video_gcs_path,
            len(self.screenshots_paths),
            len(self.transcript),
            self.summary,
            self.sentiment,
        )

    def to_dict(self):
        return {
            "local_path": self.local_path,
            "video_gcs_path": self.video_gcs_path,
            "screenshots_paths": self.screenshots_paths,
            "transcript": self.transcript,
            "summary": self.summary,
            "sentiment": self.sentiment,
        }


# used for local testing
# (intermediary between video steps and Google docs API steps)
def write_clips_to_json(clips, filename="clips.json"):
    clips_dict = [clip.to_dict() for clip in clips]
    with open(filename, "w") as f:
        json.dump(clips_dict, f, indent=4)


# CONFIG
project_id = "cpet-sandbox"
bucket_name = "cpet-autologger"
folder_prefix = "java-cloudrun-" + str(int(time.time()))
model_name = "gemini-1.5-flash-001"
fl_description = "Megan is part of Google Cloud Developer Relations. (Pronouns: they/them/theirs) This is a recording of a Friction Log session. Their topic was: {}. You are part of an automated process to generate the beginnings of a Friction Log google doc. Your first task is simply to transcribe the audio in this video chunk.".format(
    "Deploy a Java Spring application to Google Cloud Run"
)


# given a local file path (with the long video),break the video into 1-minute chunks- write all chunks to out/ directory
# also grab a screenshot every 15 seconds (4 screencaps per clip) and write temporarily to local disk
# https://stackoverflow.com/questions/67334379/cut-mp4-in-pieces-python
def chunk_video_and_grab_screenshots(video_path, chunk_length=60):
    print("🎥 Breaking the recording into 60-second chunks...")
    out_dir = "./out"  # Base output directory
    try:
        video = VideoFileClip(video_path)
        duration = video.duration
        start_time = 0
        chunk_index = 0

        while start_time < duration:
            end_time = min(start_time + chunk_length, duration)
            chunk = video.subclip(start_time, end_time)

            # Create a directory for each chunk
            chunk_dir = f"{out_dir}/chunk_{chunk_index}"
            if not os.path.exists(chunk_dir):
                os.makedirs(chunk_dir)

            # Save the video chunk
            chunk_file_name = f"{chunk_dir}/video.mp4"
            chunk.write_videofile(chunk_file_name, codec="libx264", audio_codec="aac")

            # Capture and save screenshots every 15 seconds within the chunk
            for screenshot_time in range(
                0, min(chunk_length, int(end_time - start_time)), 15
            ):
                screenshot = chunk.get_frame(screenshot_time)
                screenshot_file_name = (
                    f"{chunk_dir}/screenshot_{screenshot_time//15}.jpg"
                )
                # write screenshot to local disk
                imageio.imwrite(screenshot_file_name, screenshot)
            start_time += chunk_length
            chunk_index += 1
    except Exception as e:
        print(f"❌ Error breaking video into chunks: {e}")


# VIDEO AND SCREENSHOT UPLOAD
# param: local subdir of out, aka out/chunk_0
def upload_to_gcs(subdir):
    global project_id
    global bucket_name

    gcs_video_path = ""

    storage_client = storage.Client(project=project_id)
    bucket = storage_client.bucket(bucket_name)

    target_directory = folder_prefix + "/" + subdir + "/screenshots/"
    screenshots_paths = []
    try:
        for screenshot in os.listdir(f"./out/{subdir}"):
            if screenshot.endswith(".jpg"):
                sp = f"{target_directory}{screenshot}"
                screenshots_paths.append(sp)
                print("🖼️ Uploading screenshot to GCS: " + sp)
                blob = bucket.blob(sp)
                blob.upload_from_filename(f"./out/{subdir}/{screenshot}")
                print(
                    f"⬆️ Uploaded {screenshot} to Google Cloud Storage, bucket: {bucket_name}, directory: {target_directory}"
                )
            else:
                gcs_video_path = f"{target_directory}video.mp4"
                blob = bucket.blob(gcs_video_path)
                blob.upload_from_filename(f"./out/{subdir}/video.mp4")
                print("🎥 Uploaded video to GCS: " + gcs_video_path)

    except Exception as e:
        print(f"❌ Error uploading to GCS: {e}")
        return ""
    return gcs_video_path, screenshots_paths


# gets the full text transcript for a 1 minute video chunk
def get_transcript(video_gcs_path):
    global project_id
    global bucket_name
    global fl_description
    global model_name

    try:
        vertexai.init(project=project_id, location="us-central1")
        model = GenerativeModel(model_name=model_name)

        prompt = """
        Transcribe this one-minute video, word for word. Add punctuation to improve readability - avoid run on sentences. Return ONLY the exact transcript."""

        video_file_uri = "gs://{}/{}".format(bucket_name, video_gcs_path)
        video_file = Part.from_uri(video_file_uri, mime_type="video/mp4")
        contents = [video_file, prompt]
        response = model.generate_content(contents)
    except Exception as e:
        print(f"❌ Error getting transcript: {e}")
        return ""
    transcript = response.text
    transcript = transcript.strip()
    print("\n📜 GOT TRANSCRIPT:\n{}\n".format(transcript))
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
        
        TRANSCRIPT: {}
        """.format(
            fl_description, transcript
        )
        prompt_contents.append(text_prompt)
        for sp in screenshots_paths:
            gs_path = "gs://{}/{}".format(bucket_name, sp)
            prompt_contents.append(Part.from_uri(gs_path, mime_type="image/jpeg"))
        response = model.generate_content(prompt_contents)
    except Exception as e:
        print(f"❌ Error getting summary: {e}")
        return []
    summary = response.text.strip()
    print("\n📝 GOT SUMMARY:\n{}\n".format(summary))
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
            gs_path = "gs://{}/{}".format(bucket_name, sp)
            prompt_contents.append(Part.from_uri(gs_path, mime_type="image/jpeg"))
        response = model.generate_content(prompt_contents)
    except Exception as e:
        print(f"❌ Error getting sentiment: {e}")
        return []
    return response.text.strip()


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
    # chunk_video_and_grab_screenshots(video_path)
    clips = []

    ordered_dirs = sorted(os.listdir("./out"))
    print(ordered_dirs)
    for subdir in ordered_dirs:
        c = Clip(None, None, None, None, None, None)
        c.local_path = f"./out/{subdir}/video.mp4"
        c.video_gcs_path, c.screenshots_paths = upload_to_gcs(subdir)
        c.transcript = get_transcript(c.video_gcs_path)
        c.summary = get_summary(c.transcript, c.screenshots_paths)
        c.sentiment = get_sentiment(c.transcript, c.screenshots_paths, c.summary)
        clips.append(c)

    print("🏁 DONE PROCESSING ALL CLIPS.")
    for c in clips:
        print(c)
    # write results to local disk
    write_clips_to_json(clips)


if __name__ == "__main__":
    autologger("../test_recordings/java_cloudrun.mp4")
