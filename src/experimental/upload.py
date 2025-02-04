from flask import flash, redirect
from werkzeug.utils import secure_filename

import os
import tempfile

ALLOWED_EXTENSIONS = {"mp4"}


# Utility methods
def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def process_upload_form(request):
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
            filename = secure_filename(file.filename)

            temp_dir = tempfile.gettempdir()
            file_destination = os.path.join(temp_dir, filename)
            file.save(file_destination)
            return file_destination

    else:
        raise Exception(
            "ERROR: reached end of script without fulfilling any conditions"
        )
