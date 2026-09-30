import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from speech_transcriptor.src.main import SpeechToText

if len(sys.argv) != 2:
    sys.exit("Usage: uv run python run_transcription.py <audio_file>")
audio_path = sys.argv[1]

print(f"Transcribing: {audio_path}")
stt = SpeechToText(project="trial", client="test")
url = stt.transcribe_and_blob(audio_path)
print(f"\nDone! Transcript SAS URL:\n{url}")
