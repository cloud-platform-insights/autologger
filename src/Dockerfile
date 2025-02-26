FROM python:alpine3.12
WORKDIR /app
# run pip install first b/c it's likely more stable than the app code
COPY requirements.txt /app
RUN pip install -r requirements.txt 
COPY . /app
EXPOSE 5000
ENTRYPOINT [ "python" ] 
CMD [ "app.py" ] 