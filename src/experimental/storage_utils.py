import glob
import os
from google.cloud import storage

client = storage.Client()


def upload_dir(source_dir, destination_bucket):
    """
    Upload a complete directory, recursively, to GCS

    Return a list of all object URIs
    """

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
