# create_transcription_job.py
import logging
import time

import requests

from .transcriber_config import SERVICE_REGION, SUBSCRIPTION_KEY

from .job_csv_manager import read_jobs_csv, set_transcription_id, update_job_status

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s:%(message)s")


def create_transcription_job(audio_url, job_id: str, max_retries=3, backoff_secs=5) -> str:
    """Crea un nuevo job de transcripción en Azure Speech Service con reintentos.
    Actualiza el estado del job en el CSV.

    Args:
        audio_url (str): URL del archivo de audio en Azure Blob Storage.
        job_id (str): Identificador único del trabajo.
        max_retries (int): Número máximo de reintentos en caso de fallo.
        backoff_secs (int): Segundos de espera entre reintentos.

    Returns:
        str: transcription_id si se creó exitosamente, None en caso contrario.
    """
    base_url = f"https://{SERVICE_REGION}.api.cognitive.microsoft.com/speechtotext/v3.2/transcriptions"
    headers = {
        "Ocp-Apim-Subscription-Key": SUBSCRIPTION_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    transcription_definition = {
        "displayName": f"Transcription Job {job_id}",
        "locale": "es-ES",
        "contentUrls": [audio_url],
        "properties": {
            "diarizationEnabled": True,
            "diarization": {"speakers": {"minCount": 1, "maxCount": 15}},
            "wordLevelTimestampsEnabled": True,
            "displayFormWordLevelTimestampsEnabled": True,
            "punctuationMode": "Automatic",
            "profanityFilterMode": "Removed",
            "languageIdentification": {"candidateLocales": ["en-US", "de-DE", "es-ES"]},
        },
    }

    attempt = 0
    while attempt < max_retries:
        try:
            response = requests.post(base_url, headers=headers, json=transcription_definition,
            timeout=60
            )
            if response.status_code not in [201, 202]:
                logging.error(f"Error al iniciar la transcripción (HTTP {response.status_code}): {response.text}")
                attempt += 1
                time.sleep(backoff_secs * attempt)
                continue

            self_url = response.json().get("self")
            if not self_url:
                logging.error("No se encontró la URL 'self' en la respuesta.")
                return None

            transcription_id = self_url.rstrip("/").split("/")[-1]
            logging.info(f"Transcription job creado con ID: {transcription_id}")

            # Asignar transcription_id al trabajo en CSV y actualizar estado
            set_transcription_id(job_id, transcription_id)
            update_job_status(job_id, "transcription_status", "Transcribing")
            return transcription_id

        except requests.exceptions.RequestException as e:
            logging.exception(f"Excepción al crear la transcripción: {e}")
            attempt += 1
            time.sleep(backoff_secs * attempt)

    logging.error(f"No se pudo crear el job de transcripción después de {max_retries} reintentos.")
    update_job_status(job_id, "transcription_status", "Failed")
    return None
