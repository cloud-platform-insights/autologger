import vertexai.preview
from vertexai.generative_models import GenerativeModel, Part


def gemini_process(gcs_clip_path, gcp_project, model_name, sys_inst):

    transcript = "TRANSCRIPT_PENDING"
    summ = "TRANSCRIPT_PENDING"
    video_file = Part.from_uri(gcs_clip_path, mime_type="video/mp4")

    vertexai.init(project=gcp_project, location="us-central1")
    model = GenerativeModel(model_name=model_name)

    # TRANSCRIPTION
    print("\n TRANSCRIPTION....")
    prompt = """Transcribe this video, word for word. Add punctuation to improve readability - avoid run on sentences. Return ONLY the exact transcript."""
    print(
        "video gcs path: {}, video file: {}".format(gcs_clip_path, video_file)
    )

    contents = [video_file, prompt]
    response = model.generate_content(contents)
    transcript = response.text
    transcript = transcript.strip()

    # SUMMARIZATION WITH SENTIMENT
    print("\n SUMMARIZATION WITH SENTIMENT ANALYSIS....")
    model = model = GenerativeModel(
        model_name=model_name,
        system_instruction=[
            "You are a friction log generator. A friction log is a written record of a developer's experience. You will be given a video, the video's transcript, and some screenshots. YOUR TASK: summarize the contents of the video, using the transcript and screenshots. Use collective first person, using we pronouns. Be as detailed as possible - up to 4-5 sentences per summary. If you see hyperlinks or code, include them in your summary - not as part of the 5 sentence count. IMPORTANT: Tag sentiment as follows: ✅ Positive (This went well). ⚠️ Some developer friction (This was challenging). ❌ Significant developer friction (This was a blocker). If the summary is neutral sentiment, do not use any emoji. Always put the emoji at the BEGINNING of the summary. It should be the first character.",
            sys_inst,
        ],
    )
    prompt_contents = [
        "Transcript: " + transcript,
        video_file,
    ]
    response = model.generate_content(prompt_contents)
    summ = response.text
    summ = summ.strip()
    print("Got summary: ", summ)
    return transcript, summ
