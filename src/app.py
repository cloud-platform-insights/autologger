# EXPERIMENTAL Web application based on autologger

from flask import Flask, request, render_template
from mdutils.mdutils import MdUtils
import markdown

import upload
import video_utils
import storage_utils
import misc_utils
import genai

from config import Config

import os
import glob


app = Flask("autologger")
app.secret_key = "KbbMp_HrXRRC6se.Je-y"  # TODO: move this into config
app.config.from_object(Config)


# Routes
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload_file():

    source_video_hash = upload.process_upload_form(request)

    return render_template(
        "upload.html",
        source_video_hash=source_video_hash,
        model_name=request.form.get("model_name"),
    )


@app.route("/process", methods=["GET"])
def process_video():
    source_video_hash = request.args.get("v")
    model_name = request.args.get("m")
    gcs_bucket = app.config["GCS_BUCKET"]
    gcp_project = app.config["GCP_PROJECT"]

    # TODO: figure out a better title (can it be extracted from content?)
    topic = source_video_hash

    fl = MdUtils(file_name="out/" + source_video_hash, title=topic)

    # split into a series of small clips
    media_dir = video_utils.split_video_and_grab_screenshots(source_video_hash)

    # upload all media to GCS
    storage_utils.upload_dir(media_dir, gcs_bucket)

    print("🚧 Building your friction log")

    media_folders = sorted(next(os.walk(media_dir))[1])

    for folder in media_folders:
        app.logger.info(
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
        app.logger.info(
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

            app.logger.info("Writing final friction log to local markdown...")
            fl.create_md_file()

            app.logger.info(
                "🏁 Autologger complete. Output file at: {}.md".format(
                    "out/" + topic
                )
            )

    fl.new_header(level=1, title="Full Transcript")
    fl.new_paragraph(transcript)

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


if __name__ == "__main__":
    # this log message doesn't show up. Why not???
    app.logger.info("🤖 Beep boop. Autologger is starting up...")
    app.run(host="0.0.0.0", debug=True, port=8080)
