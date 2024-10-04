<img src="images/logo.png" width="700" align="center">
<br/>

Autologger is a friction log generator tool.

## How it works

![Workflow](images/workflow.png)

## Quickstart

_Note: This is an early prototype. It was tested on local MacOS Sonoma, using an external Drive test account._

### Requirements

* Python 3.12+ _(autologger may work on earlier versions but we develop using the latest stable version)_
* A Google Cloud Storage bucket to which you have write access
* A Google Cloud project with the following APIs enabled:
  * [Google Drive](https://console.developers.google.com/apis/api/drive.googleapis.com/)
  * [Vertex AI](https://console.cloud.google.com/apis/library/aiplatform.googleapis.com/)

### Steps

1. Clone repo.
2. `cd autologger/src/`
3. `python3 -m venv venv`
4. `source venv/bin/activate`
5. `pip install -r requirements.txt`
6. Download Google Meet recording of a friction log session to `/input`
7. Get Google Workspace OAuth client ID credentials by following [these instructions](https://developers.google.com/workspace/guides/create-credentials#oauth-client-id). Save to `src/credentials.json`.
8. Edit `config.ini` with your info.
9. Run `python autologger.py`.
10. Get the output Markdown file in the `output/` directory. Copy the contents.
11. Open a new Google Doc.
12. Click Edit > Paste as Markdown.

## Sources

- [Moviepy](https://pypi.org/project/moviepy/)
- [Mdutils](https://pypi.org/project/mdutils/)
- [Gemini on Vertex AI - Python SDK](https://cloud.google.com/vertex-ai/generative-ai/docs/start/quickstarts/quickstart-multimodal)
- [ASCII art](https://patorjk.com/software/taag/#p=display&h=2&v=2&f=Modular&t=autologger)
- [Robot emoji](https://emoji.supply/kitchen/?%F0%9F%98%A1+%F0%9F%A4%96=8ww1kx)
