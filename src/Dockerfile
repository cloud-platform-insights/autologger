FROM python:3.12-slim

# upgrade pip
RUN pip install --upgrade pip

# # get curl for healthchecks
# RUN apk add curl

# permissions and autologger user for tightened security
RUN adduser --disabled-login autologger
RUN mkdir /home/app/ && chown -R autologger:autologger /home/app
RUN mkdir -p /var/log/flask-app && touch /var/log/flask-app/flask-app.err.log && touch /var/log/flask-app/flask-app.out.log
RUN chown -R autologger:autologger /var/log/flask-app
WORKDIR /home/app
USER autologger

# copy all the files to the container
COPY --chown=autologger:autologger . .

# venv
ENV VIRTUAL_ENV=/home/app/venv

RUN export FLASK_APP=app.py
RUN pip install -r requirements.txt

# define the port number the container should expose
EXPOSE 5000

CMD ["python", "app.py"]