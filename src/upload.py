from flask import flash
from flask import redirect
from flask import session
from flask import current_app as app

import misc_utils
import storage_utils
import os

ALLOWED_EXTENSIONS = {"mp4"}


# Utility methods
def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def process_upload_form(request):
    """
    Processes the file upload form, saving the file to the upload folder
    (as configured in config.py). Return the hash of the uploaded file.
    """
    if "input_file" not in request.files:
        flash("No file part")
        return redirect("/")
    file = request.files["input_file"]
    # If the user does not select a file, the browser submits an
    # empty file without a filename.
    if file.filename == "":
        flash("No selected file")
        return redirect("/")
    if file:
        if not allowed_file(file.filename):
            uploaded_file_ext = os.path.splitext(file.filename)[-1]
            flash(
                f"Invalid file extension: `{uploaded_file_ext}` "
                + f"(allowed extensions: {ALLOWED_EXTENSIONS})"
            )
            return redirect("/")
        else:
            file_temp_path = os.path.join(
                app.config["TEMP_FOLDER"], file.filename
            )
            file.save(file_temp_path)
            source_video_hash = misc_utils.file_hash(file_temp_path)

            file_name = f"{source_video_hash}.mp4"

            local_file_path = os.path.join(
                app.config["TEMP_FOLDER"], file_name
            )

            # rename the file to the hash
            os.rename(file_temp_path, local_file_path)

            # put the file in GCS
            storage_utils.upload_file(local_file_path, session["gcs_bucket"])

            return source_video_hash

    else:
        raise Exception(
            "ERROR: reached end of script without fulfilling any conditions"
        )
