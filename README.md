<img src="images/logo.png" width="700" align="center">
<br/>

Autologger is a friction log generator tool.

## How it works

_TODO: diagram of -aaS implementation_

## Running locally

#### Requirements

* A Google Cloud Storage bucket to which you have write access
* A Google Cloud project with the following APIs enabled:
  * VertexAI

### Direct script execution
TODO: allow passing project and bucket IDs as env vars

_developed with Python 3.12; other versions may work but are not tested_

```python
  cd src
  pip install -r requirements.txt
  flask run --debug
```

### Containerized execution
TODO: allow passing project and bucket IDs as env vars
TODO: mount ADC as docker volume
TODO: change port to 8080

```sh
  docker build . -t autologger
  docker run -d -p 5000:5000 autologger
```

### As a service
TODO: allow passing bucket ID as env var (project should just use whatever project it's running in)

The built container can be run as a Cloud Run service.

## Sources

- [Moviepy](https://pypi.org/project/moviepy/)
- [Mdutils](https://pypi.org/project/mdutils/)
- [Gemini on Vertex AI - Python SDK](https://cloud.google.com/vertex-ai/generative-ai/docs/start/quickstarts/quickstart-multimodal)
- [ASCII art](https://patorjk.com/software/taag/#p=display&h=2&v=2&f=Modular&t=autologger)
- [Robot emoji](https://emoji.supply/kitchen/?%F0%9F%98%A1+%F0%9F%A4%96=8ww1kx)
