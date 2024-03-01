import os
import uuid
import subprocess
from flask import Flask, request, jsonify, render_template
from google.cloud import speech, storage
from google.oauth2 import service_account
import json
import openai
from google.cloud import secretmanager

app = Flask(__name__)

# Google Cloud Project ID
PROJECT_ID = "web-app-medai"
# Secrets IDs
OPENAI_API_KEY_SECRET_ID = "webaikey"
GOOGLE_CLOUD_CREDENTIALS_SECRET_ID = "googlesrvacc"

# Initialize Google Cloud Secret Manager client
secret_client = secretmanager.SecretManagerServiceClient()

def access_secret_version(secret_id, version_id="latest"):
    """Accesses a version of a secret from Google Cloud Secret Manager."""
    name = f"projects/{PROJECT_ID}/secrets/{secret_id}/versions/{version_id}"
    response = secret_client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")

# Fetch secrets
OPENAI_API_KEY = access_secret_version(OPENAI_API_KEY_SECRET_ID)
google_cloud_credentials_json = access_secret_version(GOOGLE_CLOUD_CREDENTIALS_SECRET_ID)

# Convert JSON credentials string to a dictionary
google_cloud_credentials_dict = json.loads(google_cloud_credentials_json)

# Setup Google Cloud and OpenAI clients with fetched secrets
storage_client = storage.Client(credentials=service_account.Credentials.from_service_account_info(google_cloud_credentials_dict))
bucket = storage_client.bucket("audioforweb")
openai.api_key = OPENAI_API_KEY

LOCAL_UPLOADS_FOLDER = "uploads"
os.makedirs(LOCAL_UPLOADS_FOLDER, exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

def upload_blob(bucket_name, source_file_path, destination_blob_name):
    """Uploads a file to the specified bucket."""
    try:
        blob = bucket.blob(destination_blob_name)
        blob.upload_from_filename(source_file_path)
        print(f"File {source_file_path} uploaded to {destination_blob_name}.")
    except Exception as e:
        print(f"Failed to upload to Google Cloud Storage: {e}")
        raise

@app.route('/upload', methods=['POST'])
def upload_audio():
    file = request.files.get('audioFile')
    if not file:
        return jsonify({'error': 'No audio file provided'}), 400

    unique_id = uuid.uuid4().hex
    raw_local_filename = f"{unique_id}_raw.wav"
    raw_local_filepath = os.path.join(LOCAL_UPLOADS_FOLDER, raw_local_filename)
    file.save(raw_local_filepath)

    local_filename = f"{unique_id}.wav"
    local_filepath = os.path.join(LOCAL_UPLOADS_FOLDER, local_filename)
    ffmpeg_command = [
        'ffmpeg', '-i', raw_local_filepath, '-acodec', 'pcm_s16le', '-ar', '44100', '-ac', '1', local_filepath
    ]
    subprocess.run(ffmpeg_command, check=True)

    cloud_filename = f"audio/{local_filename}"
    upload_blob("audioforweb", local_filepath, cloud_filename)

    transcript = transcribe_audio(f"gs://audioforweb/{cloud_filename}")
    
    transcript_filename = f"{unique_id}_transcript.txt"
    transcript_filepath = os.path.join(LOCAL_UPLOADS_FOLDER, transcript_filename)
    with open(transcript_filepath, 'w') as transcript_file:
        transcript_file.write(transcript)
    upload_blob("audioforweb", transcript_filepath, f"transcripts/{transcript_filename}")

    summary = summarize_text(transcript)

    summary_filename = f"{unique_id}_summary.txt"
    summary_filepath = os.path.join(LOCAL_UPLOADS_FOLDER, summary_filename)
    with open(summary_filepath, 'w') as summary_file:
        summary_file.write(summary)
    upload_blob("audioforweb", summary_filepath, f"summaries/{summary_filename}")
    
    return jsonify({'transcript': transcript, 'summary': summary})

def transcribe_audio(gcs_uri):
    """Transcribes the given audio file using Google Cloud Speech-to-Text."""
    client = speech.SpeechClient(credentials=service_account.Credentials.from_service_account_info(google_cloud_credentials_dict))
    audio = speech.RecognitionAudio(uri=gcs_uri)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=44100,
        language_code="en-US",
        enable_automatic_punctuation=True
    )

    operation = client.long_running_recognize(config=config, audio=audio)
    response = operation.result(timeout=90)

    return " ".join(result.alternatives[0].transcript for result in response.results)

def summarize_text(text):
    response = openai.Completion.create(
        engine="gpt-3.5-turbo-instruct",
        prompt=f"Fill out an Electronic Health Record using the information in this conversation: {text}",
        temperature=0.7,
        max_tokens=150,
        top_p=1.0,
        frequency_penalty=0.0,
        presence_penalty=0.0
    )
    return response.choices[0].text.strip()

if __name__ == '__main__':
 app.run(debug=True, port=8080)
