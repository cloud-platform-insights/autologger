import os
import tempfile


class Config:
    DEBUG = True
    TESTING = False
    SESSION_COOKIE_SECURE = True
    SECRET_KEY = os.urandom(24)
    SYSTEM_INSTRUCTIONS = "You are an automated Friction Log generator. Your job is to take a recording or transcript, and summarize the developer's journey on a specific task: each step, with the highs and lows (sentiment) of their experience."
    TEMP_FOLDER = tempfile.gettempdir()
    GCP_PROJECT = os.environ.get("GCP_PROJECT") or "cpet-stanke-sandbox"
    GCS_BUCKET = os.environ.get("GCS_BUCKET") or "autologger"
