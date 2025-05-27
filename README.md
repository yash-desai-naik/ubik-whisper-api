# Ubik Whisper API

A FastAPI-based REST API for transcribing and summarizing audio files using OpenAI's Whisper and GPT-4.1-mini models.

## Features

- Transcribe audio files (M4A, MP3, WAV, etc.) using OpenAI's Whisper model
- Summarize transcriptions using OpenAI's GPT-4.1-mini model
- Handle large audio files by splitting them into smaller chunks
- Process long transcriptions by splitting them into smaller chunks for summarization
- Extract metadata from transcriptions (dates, links, people, organizations, etc.)
- Store data using Supabase

## Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/ubik-whisper-api.git
cd ubik-whisper-api
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the root directory with your API keys:
```
OPENAI_API_KEY=your_openai_api_key
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```

4. Run the application:
```bash
uvicorn app.main:app --reload
```

## API Endpoints

- `GET /health`: Check if the API is running
- `POST /transcribe`: Submit an audio file for transcription (supports M4A, MP3, WAV, MP4, MPEG, MPGA, WEBM)
- `GET /transcribe/status/{id}`: Check the status of a transcription job
- `POST /summarize`: Submit a transcription for summarization
- `GET /summarize/status/{id}`: Check the status of a summarization job

## Usage Examples

### Complete Flow Example

Here's a complete example flow using curl commands:

#### 1. Check API Health

```bash
curl http://localhost:8000/health
```

Example response:
```json
{
  "status": "ok"
}
```

#### 2. Submit an Audio File for Transcription

```bash
curl -X POST -F "file=@your_audio_file.m4a" http://localhost:8000/transcribe
```

Example response:
```json
{
  "id": "9977c596-2155-4ccd-9660-6db7c36f8850",
  "status": "pending",
  "progress": 0,
  "transcription": null,
  "error": null
}
```

#### 3. Check Transcription Status

```bash
curl http://localhost:8000/transcribe/status/9977c596-2155-4ccd-9660-6db7c36f8850
```

Example response (in progress):
```json
{
  "id": "9977c596-2155-4ccd-9660-6db7c36f8850",
  "status": "processing",
  "progress": 0.5,
  "transcription": null,
  "error": null
}
```

Example response (completed):
```json
{
  "id": "9977c596-2155-4ccd-9660-6db7c36f8850",
  "status": "completed",
  "progress": 1.0,
  "transcription": "This is the transcribed text from your audio file...",
  "error": null
}
```

#### 4. Submit the Transcription for Summarization

```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"transcribe_id": "9977c596-2155-4ccd-9660-6db7c36f8850"}' \
  http://localhost:8000/summarize
```

Example response:
```json
{
  "id": "a1b2c3d4-5e6f-7g8h-9i0j-k1l2m3n4o5p6",
  "status": "pending",
  "progress": 0,
  "summary": null,
  "error": null
}
```

#### 5. Check Summarization Status

```bash
curl http://localhost:8000/summarize/status/a1b2c3d4-5e6f-7g8h-9i0j-k1l2m3n4o5p6
```

Example response (in progress):
```json
{
  "id": "a1b2c3d4-5e6f-7g8h-9i0j-k1l2m3n4o5p6",
  "status": "processing",
  "progress": 0.75,
  "summary": null,
  "error": null
}
```

Example response (completed):
```json
{
  "id": "a1b2c3d4-5e6f-7g8h-9i0j-k1l2m3n4o5p6",
  "status": "completed",
  "progress": 1.0,
  "summary": "# Summary of Weather Information Request\n\n## User Request\nThe user requested weather information specifically for Bodhidhara, Gujarat. (Auto-corrected to Vadodara, Gujarat)\n\n## Additional Instructions\nThe user asked for the weather information to be sent to the email address: example@gmail.com.\n\n---\n\n### Metadata\n1. **Locations Mentioned:** Vadodara, Gujarat (Auto-corrected from Bodhidhara)  \n2. **Email Address:** example@gmail.com  \n3. **Key Topics Discussed:** Weather information request",
  "error": null
}
```

### Using with Python

You can also use the API with Python:

```python
import requests

# Base URL
base_url = "http://localhost:8000"

# 1. Check API health
health_response = requests.get(f"{base_url}/health")
print(f"Health check: {health_response.json()}")

# 2. Submit audio file for transcription
with open("your_audio_file.m4a", "rb") as f:
    files = {"file": ("your_audio_file.m4a", f, "audio/m4a")}
    transcribe_response = requests.post(f"{base_url}/transcribe", files=files)

transcription_id = transcribe_response.json()["id"]
print(f"Transcription ID: {transcription_id}")

# 3. Check transcription status (you might want to poll this endpoint)
import time
while True:
    status_response = requests.get(f"{base_url}/transcribe/status/{transcription_id}")
    status_data = status_response.json()
    print(f"Transcription status: {status_data['status']}, progress: {status_data['progress']}")
    
    if status_data["status"] in ["completed", "failed"]:
        break
    
    time.sleep(5)  # Poll every 5 seconds

# 4. Submit for summarization (only if transcription was successful)
if status_data["status"] == "completed":
    summarize_response = requests.post(
        f"{base_url}/summarize", 
        json={"transcribe_id": transcription_id}
    )
    
    summary_id = summarize_response.json()["id"]
    print(f"Summary ID: {summary_id}")
    
    # 5. Check summarization status
    while True:
        summary_status_response = requests.get(f"{base_url}/summarize/status/{summary_id}")
        summary_data = summary_status_response.json()
        print(f"Summary status: {summary_data['status']}, progress: {summary_data['progress']}")
        
        if summary_data["status"] in ["completed", "failed"]:
            if summary_data["status"] == "completed":
                print(f"\nSummary:\n{summary_data['summary']}")
            break
        
        time.sleep(5)  # Poll every 5 seconds
```
