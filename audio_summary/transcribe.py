"""תמלול קובץ שמע באמצעות OpenAI Whisper API."""
import os
from openai import OpenAI

# מגבלת גודל קובץ של ה-API
MAX_FILE_SIZE_BYTES = 24 * 1024 * 1024


def transcribe_audio(client: OpenAI, audio_path: str, language: str = "he") -> str:
    """מתמלל קובץ שמע יחיד. אם הקובץ גדול מהמגבלה, מפצל אותו לחלקים."""
    size = os.path.getsize(audio_path)
    if size <= MAX_FILE_SIZE_BYTES:
        return _transcribe_single(client, audio_path, language)
    return _transcribe_chunked(client, audio_path, language)


def _transcribe_single(client: OpenAI, audio_path: str, language: str) -> str:
    with open(audio_path, "rb") as f:
        result = client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            language=language,
            response_format="text",
        )
    return str(result)


def _transcribe_chunked(client: OpenAI, audio_path: str, language: str) -> str:
    from pydub import AudioSegment

    audio = AudioSegment.from_file(audio_path)
    chunk_length_ms = 10 * 60 * 1000  # 10 דקות לכל חלק
    chunks = [audio[i:i + chunk_length_ms] for i in range(0, len(audio), chunk_length_ms)]

    transcripts = []
    tmp_dir = os.path.join(os.path.dirname(os.path.abspath(audio_path)), "_chunks_tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    try:
        for idx, chunk in enumerate(chunks):
            chunk_path = os.path.join(tmp_dir, f"chunk_{idx}.mp3")
            chunk.export(chunk_path, format="mp3")
            print(f"מתמלל חלק {idx + 1} מתוך {len(chunks)}...")
            transcripts.append(_transcribe_single(client, chunk_path, language))
            os.remove(chunk_path)
    finally:
        if os.path.isdir(tmp_dir) and not os.listdir(tmp_dir):
            os.rmdir(tmp_dir)

    return "\n".join(transcripts)
