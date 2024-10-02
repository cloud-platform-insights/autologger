import os


def make_topic_folders(source_folder: str) -> list[str]:
    topic_list = []

    video_files = [item for item in os.listdir(source_folder) 
                   if os.path.isfile(os.path.join(source_folder, item)) 
                   and item.endswith('.mp4')]

    for file in video_files:
        topic_list.append(file.split(".")[0])

    # create output directories if they don't exist
    directories = ["./clips", "./out"]

    for topic in topic_list:
        for directory in directories:
            topic_directory = os.path.join(directory, topic)
            os.makedirs(topic_directory, exist_ok=True)

    return topic_list
