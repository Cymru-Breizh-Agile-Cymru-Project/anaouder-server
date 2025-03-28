import os
import subprocess
from pathlib import Path
from xml.dom import minidom

from anaouder.asr.models import get_latest_model
from audio_utils import prepare_audio
from celery import Celery
from json_conversion import convert_from_json
from speech_to_text_tasks import SpeechToTextTask

# was 'redis://redis:6379/0'
REDIS_HOST = os.environ.get("REDIS_HOST")
REDIS_PORT = os.environ.get("REDIS_PORT")
BACKEND_CONN_URI = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"
BROKER_CONN_URI = BACKEND_CONN_URI

#
app = Celery(
    "tasks",
    broker=BROKER_CONN_URI,
    backend=BACKEND_CONN_URI,
)


#
# @todo - figure out a way to get whisper special tokens..
# in HF: transcription = processor.decode(predicted_ids, skip_special_tokens=True) # if False, then we see whisper tokens.
#
@app.task(
    name="speech_to_text",
    ignore_result=False,
    bind=True,
    base=SpeechToTextTask,
    serializer="json",
)
def speech_to_text(self, audio_file_path: str):
    print(f"Task speech to text for {audio_file_path} received")

    audio_id = Path(audio_file_path).stem
    wav_audio_file_path = prepare_audio(audio_file_path)
    json_file_path = wav_audio_file_path.with_suffix(".json")
    print("Running adskrivan")
    print(f"Writing to {json_file_path}")
    model_path = Path("/models") / get_latest_model()
    process = subprocess.Popen(
        [
            "adskrivan",
            *("-m", str(model_path)),
            *("--set-ffmpeg-path", "/usr/bin/ffmpeg"),
            *("-t", "json"),
            *("-o", str(json_file_path)),
            str(wav_audio_file_path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    output, err = process.communicate()
    print(output.decode())
    print(err.decode())
    if process.returncode != 0:
        raise RuntimeError(
            f"sub-process call to adskrivan returned a non-zero return code ({process.returncode})"
        )

    print("Converting from JSON")
    formats = convert_from_json(json_file_path)
    for format, content in formats.items():
        if format == "json":
            continue
        output_path = wav_audio_file_path.with_suffix(f".{format}")
        print(f"Writing to {output_path}")
        output_path.write_text(content)

    eaf_file_path = wav_audio_file_path.with_suffix(".eaf")
    print("Patching the ELAN file")
    doc = minidom.parseString(eaf_file_path.read_text())
    media_descriptor = doc.getElementsByTagName("MEDIA_DESCRIPTOR")[0]
    media_descriptor.setAttribute(
        "MEDIA_URL",
        f"https://stt-br.techiaith.cymru/api/get_wav/?stt_id={wav_audio_file_path.stem}",
    )
    media_descriptor.removeAttribute("RELATIVE_MEDIA_URL")
    eaf_file_path.write_bytes(doc.toxml(encoding="UTF-8"))
    print(f"Saved output to {eaf_file_path}")

    # Return some stuff
    result = {"id": audio_id, "version": 2, "success": True}
    return result
