# EXPERIMENTAL Web application based on autologger

from flask import Flask, request, redirect, render_template, url_for

# from flask import flash, redirect

import experimental.upload as upload
import experimental.video_utils as video_utils

import logging
import sys

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
    return redirect(url_for(".process_video", file_path=uploaded_file_path))


@app.route("/process", methods=["GET"])
def process_video():
    file_path = request.args.get("file_path")
    subclips = video_utils.split_video(file_path)
    return render_template(
        "process.html", file_path=file_path, subclips=subclips
    )


if __name__ == "autologger":
    # this log message doesn't show up. Why not???
    app.logger.info("🤖 Beep boop. Autologger is starting up...")
    app.run(debug=True, port=5000)
