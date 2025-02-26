import glob
import os
from google.cloud import storage
from flask import current_app as app


def download_file_to_tempdir(blob_name, bucket_name):
    """
    Download a file from GCS
    """
    client = storage.Client()
    bucket = client.get_bucket(bucket_name)
    blob = bucket.blob(blob_name)

    # save to working location
    destination = os.path.join(app.config["TEMP_FOLDER"], blob_name)
    blob.download_to_filename(destination)
    return destination


def upload_file(source_file, destination_bucket):
    """
    Upload a file to GCS"""
    client = storage.Client()
    bucket = client.get_bucket(destination_bucket)

    file_name = os.path.basename(source_file)
    blob = bucket.blob(file_name)
    blob.upload_from_filename(source_file)


def upload_dir(source_dir, destination_bucket):
    """
    Upload a complete directory, recursively, to GCS

    Return a list of all object URIs
    """

    client = storage.Client()

    rel_paths = glob.glob(source_dir + "/**", recursive=True)
    bucket = client.get_bucket(destination_bucket)

    # the name of the source_dir is a hash of the contents of the original
    # file; if it has already been uploaded, skip.
    video_id = source_dir.split(os.sep)[-1]

    blobs_in_storage = [
        blob.name
        for blob in client.list_blobs(
            destination_bucket, match_glob=f"**/{video_id}**"
        )
    ]

    if len(blobs_in_storage) > 0:
        print("Video has already been uploaded to storage; skipping upload.")
    else:
        print("Uploading...")
        for local_file in rel_paths:
            # for destination, remove the full (local filesystem) path; use
            # only folder specific to ths input file
            stripped_path = local_file.replace(
                os.sep.join(source_dir.split(os.sep)[:-1]), ""
            )
            # strip leading slash
            if stripped_path[0] == "/":
                stripped_path = stripped_path[1:]
            if os.path.isfile(local_file):
                blob = bucket.blob(stripped_path)
                print(f"Uploading: {local_file}")
                blob.upload_from_filename(local_file)

        blobs_in_storage = [
            blob.name
            for blob in client.list_blobs(
                destination_bucket, match_glob=f"**/{video_id}**"
            )
        ]

    return sorted(blobs_in_storage)
