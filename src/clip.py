# One Clip represents a clip of the input video. The length of each clip is determined by the configurable "interval" field. (Seconds) - Default = 60 second clips
class Clip:
    def __init__(
        self,
        topic,
        clip_number,
        video_gcs_path,
        ss_gcs_paths,
        ss_drive_paths,
        transcript,
        summary,
    ):
        self.topic = topic
        self.clip_number = clip_number
        self.video_gcs_path = video_gcs_path
        self.ss_gcs_paths = ss_gcs_paths
        self.ss_drive_paths = ss_drive_paths
        self.transcript = transcript
        self.summary = summary

    # used for debug logging
    def __str__(self):
        return """ 
        --------------------------------
        🎞️ Clip #{} - {}
        Video GCS Path: {}
        Screenshots GCS Paths: {} 
        Screenshots Google Drive Paths: {} 
        Transcript: {}
        Summary: {}
        --------------------------------
        """.format(
            self.clip_number,
            self.topic,
            self.video_gcs_path,
            self.ss_gcs_paths,
            self.ss_drive_paths,
            self.transcript,
            self.summary,
        )

    # used to write to json
    def to_dict(self):
        return {
            "topic": self.topic,
            "clip_number": self.clip_number,
            "video_gcs_path": self.video_gcs_path,
            "ss_gcs_paths": self.ss_gcs_paths,
            "ss_drive_paths": self.ss_drive_paths,
            "transcript": self.transcript,
            "summary": self.summary,
        }
