# process_transcription.py
import json
import os
import logging
import re
from typing import Optional

# Configuración del logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s:%(message)s")


def parse_iso_duration(duration_str: str) -> Optional[float]:
    """
    Convierte una duración en formato ISO 8601 (e.g., "PT1H2M3.04S") a segundos como float.

    Args:
        duration_str (str): Duración en formato ISO 8601.

    Returns:
        Optional[float]: Duración en segundos. Retorna None si el formato no es válido.
    """
    try:
        pattern = re.compile(
            r"PT" r"(?:(?P<hours>\d+)H)?" r"(?:(?P<minutes>\d+)M)?" r"(?:(?P<seconds>\d+(?:\.\d+)?)S)?"
        )
        match = pattern.match(duration_str)
        if not match:
            logging.warning(f"Formato de duración no soportado: {duration_str}")
            return None
        parts = match.groupdict()
        hours = float(parts["hours"]) if parts["hours"] else 0.0
        minutes = float(parts["minutes"]) if parts["minutes"] else 0.0
        seconds = float(parts["seconds"]) if parts["seconds"] else 0.0
        total_seconds = hours * 3600 + minutes * 60 + seconds
        return total_seconds
    except Exception as e:
        logging.error(f"Error al parsear duración '{duration_str}': {e}")
        return None


def process_transcription_file(file_path: str, output_path: str) -> None:
    """
    Procesa un archivo de transcripción JSON para extraer speakers, timestamps y texto.
    Combina bloques consecutivos del mismo speaker.
    Utiliza el campo 'display' para el texto.
    Formatea los tiempos en segundos enteros.
    Guarda el resultado en un archivo preprocesado.

    Args:
        file_path (str): Ruta al archivo JSON de transcripción descargado.
        output_path (str): Ruta donde se guardará el JSON preprocesado.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        logging.error(f"Error al leer el archivo {file_path}: {e}")
        return

    processed_data = []
    current_speaker: Optional[str] = None
    current_start: Optional[int] = None
    current_end: Optional[int] = None
    current_text: str = ""

    # Iterar sobre las frases reconocidas
    for phrase in data.get("recognizedPhrases", []):
        speaker_id = phrase.get("speaker")
        offset_str = phrase.get("offset")
        duration_str = phrase.get("duration")
        n_best = phrase.get("nBest", [])

        # Validar la presencia de offset y duration
        if not offset_str or not duration_str:
            logging.warning(f"Falta 'offset' o 'duration' en la frase: {phrase}")
            continue

        # Validar la presencia de nBest y display
        if not n_best:
            logging.warning(f"No hay 'nBest' en la frase: {phrase}")
            continue

        best_n = n_best[0]
        display_text = best_n.get("display", "").strip()

        if not display_text:
            logging.warning(f"Falta 'display' en la frase: {phrase}")
            continue

        # Convertir 'offset' y 'duration' a segundos
        start_time_sec = parse_iso_duration(offset_str)
        duration_sec = parse_iso_duration(duration_str)

        if start_time_sec is None or duration_sec is None:
            logging.warning(f"Error al convertir 'offset' o 'duration' en la frase: {phrase}")
            continue

        # Redondear a enteros
        start_time_sec = int(start_time_sec)
        end_time_sec = int(start_time_sec + duration_sec)

        # Formatear el speaker (ejemplo: Speaker_1)
        speaker = f"Speaker_{speaker_id}" if speaker_id is not None else "Unknown"

        if speaker == current_speaker:
            # Si el mismo speaker continúa, extendemos el bloque actual
            current_end = end_time_sec
            current_text += " " + display_text
        else:
            # Si es un nuevo speaker, guardar el bloque anterior (si existe)
            if current_speaker is not None:
                processed_data.append(
                    {
                        "speaker": current_speaker,
                        "startTime": str(current_start),
                        "endTime": str(current_end),
                        "text": current_text.strip(),
                    }
                )
            # Iniciar un nuevo bloque
            current_speaker = speaker
            current_start = start_time_sec
            current_end = end_time_sec
            current_text = display_text

    # Añadir el último bloque
    if current_speaker is not None:
        processed_data.append(
            {
                "speaker": current_speaker,
                "startTime": str(current_start),
                "endTime": str(current_end),
                "text": current_text.strip(),
            }
        )

    # Guardar el resultado preprocesado
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(processed_data, f, ensure_ascii=False, indent=4)
        logging.info(f"Archivo preprocesado guardado en: {output_path}")
    except Exception as e:
        logging.error(f"Error al guardar el archivo preprocesado: {e}")


def process_all_transcriptions(downloaded_dir: str, processed_dir: str) -> None:
    """
    Procesa todos los archivos de transcripción JSON en un directorio dado.
    Guarda los archivos preprocesados con el prefijo 'preprocessed_'.

    Args:
        downloaded_dir (str): Directorio donde se encuentran los archivos JSON descargados.
        processed_dir (str): Directorio donde se guardarán los archivos JSON preprocesados.
    """
    if not os.path.exists(processed_dir):
        os.makedirs(processed_dir)

    for file_name in os.listdir(downloaded_dir):
        # Se excluyen los que ya están preprocesados para evitar sobreescritura infinita
        if file_name.endswith(".json") and not file_name.startswith("preprocessed_"):
            file_path = os.path.join(downloaded_dir, file_name)
            output_file = os.path.join(processed_dir, f"preprocessed_{file_name}")
            logging.info(f"Procesando archivo: {file_path}")
            process_transcription_file(file_path, output_file)


if __name__ == "__main__":
    # Ejemplo de uso
    downloaded_directory = "./transcripciones_descargadas"
    processed_directory = "./transcripciones_procesadas"
    process_all_transcriptions(downloaded_directory, processed_directory)
