# autologger

### breaking down the problem 

#### **Google Meet --> Transcript + Recording --> Cloud Storage Bucket** 

(manual upload)

#### Transcript + recording processing (non AI)

Grab screenshots every minute

Interleave 

#### Transcript + recording processing (AI) 

Summarize transcript chunks 

Sentiment analysis on transcript chunks 

Optionally - Include images (screenshot) corresponding to timestamp of transcript chunk 

#### Write via Google Docs API  

Formatting (eg. highlight colors)? 
Or use emoji to indicate sentiment? 

### sources 

- [Google Docs API - Python client](https://developers.google.com/docs/api/quickstart/python)