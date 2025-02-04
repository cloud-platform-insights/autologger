# EXPERIMENTAL Web application based on autologger

from flask import Flask, request, redirect, render_template, url_for

# from flask import flash, redirect

import experimental.upload as upload

app = Flask(__name__)
app.secret_key = "KbbMp_HrXRRC6se.Je-y"


# Routes
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload_file():
    uploaded_file_path = upload.process_upload_form(request)
    return redirect(url_for(".process_video", file_path=uploaded_file_path))


@app.route("/process", methods=["GET"])
def process_video():
    file_path = request.args.get("file_path")
    return render_template("process.html", file_path=file_path)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
