from google.cloud import storage
from moviepy.editor import VideoFileClip
import imageio
import os
import json


# Helper, used for local testing
# (intermediary between video steps and Google docs API steps)
def write_clips_to_json(clips, filename="clips.json"):
    clips_dict = [clip.to_dict() for clip in clips]
    with open(filename, "w") as f:
        json.dump(clips_dict, f, indent=4)


# given a local file path (with the long video),break the video into 30-second chunks- write all chunks to out/ directory
# also grab a screenshot every 15 seconds (2 screencaps per clip) and write temporarily to local disk
# https://stackoverflow.com/questions/67334379/cut-mp4-in-pieces-python
def chunk_video_and_grab_screenshots(video_path, chunk_length=30):
    print("🎥 Breaking the recording into 30-second chunks...")
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
def upload_to_gcs(project_id, bucket_name, folder_prefix, subdir):
    formatted_gcs_video_path = ""

    storage_client = storage.Client(project=project_id)
    bucket = storage_client.bucket(bucket_name)

    local_directory = f"./out/{subdir}"
    target_directory = "{}/{}".format(folder_prefix, subdir)

    screenshots_paths = []
    try:
        for screenshot in os.listdir(f"./out/{subdir}"):
            if screenshot.endswith(".jpg"):
                # gcs screenshot path
                sp = f"{target_directory}/screenshots/{screenshot}"
                screenshots_paths.append("gs://{}/{}".format(bucket_name, sp))
                # print("🖼️ Uploading screenshot to GCS: " + sp)
                blob = bucket.blob(sp)
                blob.upload_from_filename(f"{local_directory}/{screenshot}")
                # print(
                #     f"⬆️ Uploaded {screenshot} to Google Cloud Storage, bucket: {bucket_name}, directory: {target_directory}"
                # )
            else:
                gcs_video_path = f"{target_directory}/video.mp4"
                blob = bucket.blob(gcs_video_path)
                blob.upload_from_filename(f"{local_directory}/video.mp4")
                formatted_gcs_video_path = "gs://{}/{}".format(
                    bucket_name, gcs_video_path
                )
                # print("🎥 Uploaded video to GCS: " + formatted_gcs_video_path)

    except Exception as e:
        print(f"❌ Error uploading to GCS: {e}")
        return ""
    return formatted_gcs_video_path, screenshots_paths
