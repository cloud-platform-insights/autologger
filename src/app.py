# EXPERIMENTAL Web application based on autologger

from flask import Flask, request, redirect, render_template, url_for
from mdutils.mdutils import MdUtils
from mdutils.tools.Html import Html

# from flask import flash, redirect

import experimental.upload as upload
import experimental.video_utils as video_utils
import experimental.storage_utils as storage_utils
import experimental.genai as genai
from clip import Clip

import logging
import sys
import json
import os
import hashlib
import base64  # TODO: extract the base64 conversion to a helper

# config vars
# TODO: extract these to a config
system_instructions = """You are an automated Friction Log generator. Your job is to take a recording or transcript, and summarize the developer's journey on a specific task: each step, with the highs and lows (sentiment) of their experience."""


app = Flask("autologger")
app.secret_key = "KbbMp_HrXRRC6se.Je-y"

handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(
    logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
)
app.logger.addHandler(handler)
app.logger.setLevel(logging.INFO)


# Routes
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload_file():
    uploaded_file_path = upload.process_upload_form(request)
    app.logger.info(f"uploaded file: {uploaded_file_path}")
    return redirect(
        url_for(
            ".process_video",
            file_path=uploaded_file_path,
            gcs_bucket=request.form.get("gcs_bucket"),
            gcp_project=request.form.get("gcp_project"),
            model_name=request.form.get("model_name"),
        )
    )


@app.route("/process", methods=["GET"])
def process_video():

    source_video_file = request.args.get("file_path")
    topic = os.path.basename(source_video_file)

    gcs_bucket = request.args.get("gcs_bucket")
    project_id = request.args.get("gcp_project")
    model_name = request.args.get("model_name")

    # use hash of file as a unique identifier
    with open(source_video_file, "rb") as video_file:
        source_video_hash = hashlib.md5(video_file.read()).hexdigest()
        video_file.close()

    fl = MdUtils(file_name="out/" + source_video_hash, title=topic)

    # split into a series of small clips
    media_dir = video_utils.split_video_and_grab_screenshots(
        source_video_file, source_video_hash
    )

    # upload all media to GCS
    uploaded_media = storage_utils.upload_dir(media_dir, gcs_bucket)

    print("🚧 Building your friction log")

    media_folders = sorted(next(os.walk(media_dir))[1])

    for folder in media_folders:
        logging.info(
            "\nGenerating transcript and summary/sentiment with Gemini..."
        )

        gcs_clip_path = (
            f"gs://{gcs_bucket}/{source_video_hash}/{folder}/video.mp4"
        )

        transcript, summary = genai.gemini_process(
            gcs_clip_path, project_id, model_name, system_instructions
        )
        logging.info(
            "📝 Writing summary and screenshots to Friction Log markdown..."
        )
        fl.new_paragraph(summary)

        # Add images to markdown
        # TODO: make this dynamic, not hardcoded to 2 (duh)
        for idx in ["0", "1"]:
            try:
                with open(
                    f"{media_dir}/{folder}/screenshot_{idx}.jpg", "rb"
                ) as img:
                    s = base64.b64encode(img.read())

                    fl.new_paragraph(
                        text=f"![{folder}/screenshot_{idx}](data:image/png;base64,{s.decode("utf-8")})"
                    )
            except Exception as e:
                logging.error(f"Error processing screenshot {idx}: {e}")

            logging.info("Writing final friction log to local markdown...")
            fl.create_md_file()

            logging.info(
                "🏁 Autologger complete. Output file at: {}.md".format(
                    "out/" + topic
                )
            )

    return render_template(
        "process.html",
        source_video_file=source_video_file,
        media_dir=media_dir,
        uploaded_media=json.dumps(uploaded_media, indent=6),
        friction_markdown=fl.get_md_text(),
    )


if __name__ == "autologger":
    # this log message doesn't show up. Why not???
    app.logger.info("🤖 Beep boop. Autologger is starting up...")
    app.run(debug=True, port=5000)
