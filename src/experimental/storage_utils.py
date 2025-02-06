import glob
import os
from google.cloud import storage

client = storage.Client()


def upload_dir(source_dir, destination_bucket):
    """
    Upload a complete directory, recursively, to GCS

    Return a list of all object URIs
    """
    
    print(destination_bucket)
    
    rel_paths = glob.glob(source_dir + "/**", recursive=True)
    bucket = client.get_bucket(destination_bucket)

    uploaded_objects = []
    

    for local_file in rel_paths:
        remote_path = (
            f'autologger_media/{"/".join(local_file.split(os.sep)[1:])}'
        )
        if os.path.isfile(local_file):
            blob = bucket.blob(remote_path)
            blob.upload_from_filename(local_file)
            uploaded_objects.append(remote_path)

    return uploaded_objects
