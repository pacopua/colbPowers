import os
import uuid
import json
import logging
import subprocess
import tempfile
import imageio_ffmpeg
from .blob_utils import upload_file_to_blob, get_blob_content_as_text
from .transcriber import transcribe
from .job_csv_manager import create_job_entry

# Make sure logging is set up
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def _compress_audio(input_path: str, output_path: str) -> None:
    """Convert audio to mono 16kHz 32kbps MP3 using bundled ffmpeg."""
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    result = subprocess.run(
        [ffmpeg_exe, "-y", "-i", input_path, "-ac", "1", "-ar", "16000", "-b:a", "32k", output_path],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg compression failed: {result.stderr[-500:]}")


class SpeechToText:
    def __init__(self, project, client):
        self.project = project
        self.client = client

    def transcribe_and_blob(self, audio_file_path: str) -> str:
        """
        Transcribe the given audio file, convert result to text format, upload to blob, return SAS URL.
        """
        logger.info(f"Starting transcription for {audio_file_path}")
        
        # 1. Upload audio to blob
        # We create a unique folder for this transcription job
        unique_id = str(uuid.uuid4())
        file_name = os.path.basename(audio_file_path)
        
        # We don't necessarily need the client/project structure in the blob for functionality,
        # but it helps organization.
        # However, new_version_speech_transcriptor logic doesn't use folders for jobs usually.
        # But we pass the SAS URL.
        
        # Uploading to a location.
        # Let's mirror the old structure: client/project/hash/...
        # But for simplicity just use unique_id.
        blob_folder = f"transcriptions/{unique_id}"

        # Compress audio to mono 16kHz 32kbps MP3 before uploading
        compressed_path = os.path.join(tempfile.gettempdir(), f"{unique_id}_compressed.mp3")
        try:
            logger.info(f"Compressing audio: {audio_file_path} -> {compressed_path}")
            _compress_audio(audio_file_path, compressed_path)
            upload_path = compressed_path
            file_name = os.path.splitext(file_name)[0] + ".mp3"
            logger.info(f"Compressed size: {os.path.getsize(compressed_path) / 1024 / 1024:.1f} MB")
        except Exception as e:
            logger.warning(f"Compression failed, uploading original: {e}")
            upload_path = audio_file_path

        # This returns the SAS URL
        try:
            audio_sas_url = upload_file_to_blob(blob_name=file_name, file_path=upload_path, folder_path=blob_folder)
            logger.info(f"Audio uploaded to: {audio_sas_url}")
        except Exception as e:
            logger.error(f"Failed to upload audio: {e}")
            raise e

        # 2. Call transcribe
        job_id = unique_id 
        
        # Create a job entry in the local CSV so that the transcriber can update status
        try:
            create_job_entry(
                job_id=job_id,
                audio_url=audio_sas_url,
                docx_template_path="N/A",  # Not used in this context
                acta_details={
                    "titulo": f"Start for {self.project}",
                    "numero_acta": "N/A"
                }
            )
        except Exception as e:
            logger.error(f"Failed to create job entry locally: {e}")
            # Depending on strictness, we might want to continue or fail. 
            # If fail here, transcribe() will fail because it expects the job entry.
            raise e
        
        # result_json_file_name is just the filename (e.g. "transcription_{recording_name}.json")
        try:
            result_json_file_name = transcribe(audio_sas_url, job_id)
        except Exception as e:
            logger.error(f"Transcribe call failed: {e}")
            raise e
        
        if not result_json_file_name:
            raise RuntimeError("Transcription failed or returned no result.")

        # 3. Download the JSON result
        # The result is stored in 'transcriptions/preprocessed' folder in the "speech-issues" container by default
        # The result_json_file_name is "transcription_<recording_name>.json"
        
        json_blob_path = f"transcriptions/preprocessed/{result_json_file_name}"
        logger.info(f"Downloading result from: {json_blob_path}")

        try:
            # We need to read the JSON content.
            # get_blob_content_as_text fetches entire blob content.
            json_text = get_blob_content_as_text(json_blob_path)
            data = json.loads(json_text)
        except Exception as e:
            logger.error(f"Failed to download/parse result json: {e}")
            raise RuntimeError(f"Failed to download/process transcription result json: {e}")

        # 4. Convert JSON to text format
        transcript_text = ""
        # The data is a list of blocks like [{"speaker": "Speaker_1", "text": "..."}]
        if isinstance(data, list):
            for block in data:
                speaker = block.get("speaker", "Unknown")
                text = block.get("text", "")
                transcript_text += f"[{speaker}]: {text}\n"
        else:
            # Fallback if format is different
             transcript_text = str(data)

        # 5. Upload the text transcript to blob
        # We upload it so frontend can download it via SAS URL
        text_blob_name = "transcription.txt"
        
        # Create temp file to upload
        tmp_path = os.path.join(tempfile.gettempdir(), f"{unique_id}_transcription.txt")
        with open(tmp_path, 'w') as tmp:
            tmp.write(transcript_text)
            
        try:
            # Upload to the same unique folder as the input audio
            text_sas_url = upload_file_to_blob(blob_name=text_blob_name, file_path=tmp_path, folder_path=blob_folder)
            logger.info(f"Transcript text uploaded to: {text_sas_url}")
            return text_sas_url
        finally:
            for p in (tmp_path, compressed_path):
                if os.path.exists(p):
                    try:
                        os.remove(p)
                    except Exception:
                        pass
