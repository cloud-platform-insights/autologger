import logging
import os
import tempfile

from moviepy import VideoFileClip

log = logging.getLogger("autologger.video_utils")


def split_video(video_path, clip_length=60):
    log.info(f"🎥 Breaking your video into {clip_length}-second clips.")
    clip_length = int(clip_length)
    out_dir = tempfile.gettempdir()
    clips_generated = []

    video = VideoFileClip(video_path)
    duration = video.duration
    start_time = 0
    clip_index = 0

    while start_time < duration:
        end_time = min(start_time + clip_length, duration)
        clip = video.subclipped(start_time, end_time)
        clip_dir = f"{out_dir}/clip_{clip_index}"
        if not os.path.exists(clip_dir):
            os.makedirs(clip_dir)
        clip_file_name = f"{clip_dir}/video.mp4"
        clip.write_videofile(
            clip_file_name, codec="libx264", audio_codec="aac"
        )
        clips_generated.append(clip_file_name)
        start_time += clip_length
        clip_index += 1

    return clips_generated


# # splits the input video into [interval]-second clips. grabs 2 screenshots per clip.

#     try:
#         video = VideoFileClip(video_path)
#         duration = video.duration
#         start_time = 0
#         clip_index = 0

#         while start_time < duration:
#             end_time = min(start_time + clip_length, duration)
#             clip = video.subclip(start_time, end_time)
#             clip_dir = f"{out_dir}/clip_{clip_index}"
#             if not os.path.exists(clip_dir):
#                 os.makedirs(clip_dir)
#             clip_file_name = f"{clip_dir}/video.mp4"
#             clip.write_videofile(
#                 clip_file_name, codec="libx264", audio_codec="aac"
#             )

#             # Capture and save screenshots every 30 seconds within the clip
#             for screenshot_time in range(
#                 0, min(clip_length, int(end_time - start_time)), 30
#             ):
#                 screenshot = clip.get_frame(screenshot_time)
#                 screenshot_file_name = (
#                     f"{clip_dir}/screenshot_{screenshot_time//30}.jpg"
#                 )
#                 imageio.imwrite(screenshot_file_name, screenshot)
#             start_time += clip_length
#             clip_index += 1
#     except Exception as e:
#         logging.error(f"❌ Error breaking video into clips: {e}")
#         sys.exit(1)
#     logging.info(
#         "✂️ Successfully split video into clips + grabbed screenshots. Ready for Gemini processing."
#     )
