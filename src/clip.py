class Clip:
    def __init__(
        self,
        video_gcs_path,
        screenshots_paths,
        transcript,
        summary,
        sentiment,
    ):
        self.video_gcs_path = video_gcs_path
        self.screenshots_paths = screenshots_paths
        self.transcript = transcript
        self.summary = summary
        self.sentiment = sentiment

    def __str__(self):
        return """ 
        --------------------------------
        🎞️ Clip:
        Video GCS path: {}
        # Screenshots paths: {}
        Transcript length: {}  
        Summary: {}
        Sentiment: {}
        --------------------------------
        """.format(
            self.video_gcs_path,
            len(self.screenshots_paths),
            len(self.transcript),
            self.summary,
            self.sentiment,
        )

    def to_dict(self):
        return {
            "video_gcs_path": self.video_gcs_path,
            "screenshots_paths": self.screenshots_paths,
            "transcript": self.transcript,
            "summary": self.summary,
            "sentiment": self.sentiment,
        }
