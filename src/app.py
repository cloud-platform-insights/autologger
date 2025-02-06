# EXPERIMENTAL Web application based on autologger

from flask import Flask, request, redirect, render_template, url_for

# from flask import flash, redirect

import experimental.upload as upload
import experimental.video_utils as video_utils
import experimental.storage_utils as storage_utils

import logging
import sys
import tempfile
import os

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
        )
    )


@app.route("/process", methods=["GET"])
def process_video():

    source_video_file = request.args.get("file_path")
    gcs_bucket = request.args.get("gcs_bucket")

    # write to a temp location (to avoid "read-only filesystem" issues)
    out_dir = os.path.join(
        tempfile.gettempdir(),
        # name the destination folder according to the input file
        os.path.basename(source_video_file).replace(".", "_"),
    )
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    # split into a series of small clips
    subclip_dirs = video_utils.split_video_and_grab_screenshots(
        source_video_file, out_dir
    )

    # upload all media to GCS
    uploaded_media = storage_utils.upload_dir(out_dir, gcs_bucket)

    return render_template(
        "process.html",
        source_video_file=source_video_file,
        out_dir=out_dir,
        subclip_dirs=subclip_dirs,
        uploaded_media=uploaded_media,
    )


if __name__ == "autologger":
    # this log message doesn't show up. Why not???
    app.logger.info("🤖 Beep boop. Autologger is starting up...")
    app.run(debug=True, port=5000)
