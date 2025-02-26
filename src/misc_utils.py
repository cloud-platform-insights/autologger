import hashlib
import base64


def file_hash(input_file_path: str) -> str:
    with open(input_file_path, "rb") as video_file:
        source_video_hash = hashlib.md5(video_file.read()).hexdigest()
        video_file.close()
    return source_video_hash


def image_to_base64(input_file_path: str) -> str:
    with open(input_file_path, "rb") as img:
        s = base64.b64encode(img.read())

    return s.decode("utf-8")
