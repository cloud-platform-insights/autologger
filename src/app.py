# EXPERIMENTAL Web application based on autologger

from flask import Flask, request, redirect, render_template, session, url_for
from mdutils.mdutils import MdUtils
import markdown

import experimental.upload as upload
import experimental.video_utils as video_utils
import experimental.storage_utils as storage_utils
import experimental.misc_utils as misc_utils
import experimental.genai as genai

from config import Config

import logging
import sys
import os
import glob


app = Flask("autologger")
app.secret_key = "KbbMp_HrXRRC6se.Je-y"  # TODO: move this into config
app.config.from_object(Config)

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
    source_video_hash = upload.process_upload_form(request)

    # set user's config choices to session
    session["gcs_bucket"] = request.form.get("gcs_bucket")
    session["gcp_project"] = request.form.get("gcp_project")
    session["model_name"] = request.form.get("model_name")

    return redirect(url_for(".process_video", v=source_video_hash))


@app.route("/process", methods=["GET"])
def process_video():
    source_video_hash = request.args.get("v")

    # TODO: figure out a better title (can it be extracted from content?)
    topic = source_video_hash

    gcs_bucket = session["gcs_bucket"]
    gcp_project = session["gcp_project"]
    model_name = session["model_name"]

    fl = MdUtils(file_name="out/" + source_video_hash, title=topic)

    # split into a series of small clips
    media_dir = video_utils.split_video_and_grab_screenshots(source_video_hash)

    # upload all media to GCS
    storage_utils.upload_dir(media_dir, gcs_bucket)

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
            gcs_clip_path,
            gcp_project,
            model_name,
            app.config["SYSTEM_INSTRUCTIONS"],
        )
        logging.info(
            "📝 Writing summary and screenshots to Friction Log markdown..."
        )
        fl.new_paragraph(summary)

        # Add images to markdown

        for screenshot in glob.glob(
            f"{media_dir}/{folder}/screenshot_[0-9].jpg"
        ):

            image_as_base64 = misc_utils.image_to_base64(screenshot)
            # print(image_as_base64)

            fl.new_paragraph(
                text=f"![screenshot](data:image/png;base64,{image_as_base64})"
            )

            logging.info("Writing final friction log to local markdown...")
            fl.create_md_file()

            logging.info(
                "🏁 Autologger complete. Output file at: {}.md".format(
                    "out/" + topic
                )
            )

    friction_html = markdown.markdown(fl.get_md_text())

    return render_template(
        "process.html",
        friction_html=friction_html,
        friction_markdown=fl.get_md_text(),
    )


# for dev purposes -- render the "proces" page witout actually
# processing the video
@app.route("/process_mock", methods=["GET"])
def process_mock():
    return render_template(
        "process.html", friction_html="foo", friction_markdown="bar"
    )


if __name__ == "autologger":
    # this log message doesn't show up. Why not???
    app.logger.info("🤖 Beep boop. Autologger is starting up...")
    app.run(debug=True, port=5000)
