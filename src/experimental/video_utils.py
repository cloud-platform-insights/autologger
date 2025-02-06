import logging
import os

from moviepy import VideoFileClip
import imageio

log = logging.getLogger("autologger.video_utils")


def split_video_and_grab_screenshots(
    source_video_file, out_dir, clip_length=60
):
    """ Take the source file and split into N subclips of length `clip_length`.
      Return a list of the paths of the output folders
    """
    log.info(f"🎥 Breaking your video into {clip_length}-second clips.")
    clip_length = int(clip_length)

    video = VideoFileClip(source_video_file)
    duration = video.duration
    start_time = 0
    clip_index = 0

    while start_time < duration:
        end_time = min(start_time + clip_length, duration)
        clip = video.subclipped(start_time, end_time)
        clip_dir = os.path.join(out_dir, f"clip_{clip_index}")
        if not os.path.exists(clip_dir):
            os.makedirs(clip_dir)
        clip_file_name = f"{clip_dir}/video.mp4"
        clip.write_videofile(
            clip_file_name, codec="libx264", audio_codec="aac"
        )
        #  Capture and save screenshots every 30 seconds within the clip
        for screenshot_time in range(
            0, min(clip_length, int(end_time - start_time)), 30
        ):
            screenshot = clip.get_frame(screenshot_time)
            screenshot_file_name = (
                f"{clip_dir}/screenshot_{screenshot_time//30}.jpg"
            )
            imageio.imwrite(screenshot_file_name, screenshot)
        start_time += clip_length
        clip_index += 1