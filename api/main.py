import os
import traceback
import uuid
from pathlib import Path

import aiofiles
from celery import Celery
from celery.result import AsyncResult
from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from files_store import (
    append_data_chunk,
    delete_all_files,
    get_audio_file_path,
    get_if_exists_file_path,
    save_sound_file,
)
from slowapi import Limiter
from slowapi.util import get_remote_address

# logger = logging.getLogger(__name__)
from techiaith_job_queue_client import Job, addJob, cancelJob

UPLOAD_DIR = "/recordings"

REDIS_HOST = os.environ.get("REDIS_HOST")
REDIS_PORT = os.environ.get("REDIS_PORT")
BACKEND_CONN_URI = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"
BROKER_CONN_URI = BACKEND_CONN_URI

app = FastAPI()

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


tasks = dict()
celery = Celery("tasks", broker=BROKER_CONN_URI, backend=BACKEND_CONN_URI)

limiter = Limiter(key_func=get_remote_address)


API_HOST = "localhost:5511/"


@app.get("/version/")
async def version():
    return {"version": 2}


@app.get("/get_status/")
async def get_status(stt_id):
    # mae 'tasks' yn dict, yn y RAM, sydd yn cynnwys task_ids pob job sydd
    # wedi mynd i Celery/Redis.
    task_status = "UNKNOWN"
    if stt_id in tasks:
        task_result = AsyncResult(tasks[stt_id])
        task_status = task_result.status
    # else
    # galw ar y jobs API i wybod os yw'r stt_id dal yn aros am callback.
    # Dyle hyn gweithio os yw'r gweinydd wedi ei ail-gychwyn.

    #
    result = {"version": 2, "status": task_status}

    #
    return result


@app.post("/keyboard/", response_class=FileResponse)
async def transcribe_for_keyboard(audio_file: UploadFile = File(...)):
    stt_id = str(uuid.uuid4())
    audio_file_path, audio_file_size = await save_sound_file(stt_id, audio_file)
    if audio_file_size < 480000:
        transcription_task = celery.send_task("speech_to_text", args=(audio_file_path,))
        task_result = transcription_task.get(timeout=60.0)
        txt_file_path = Path(os.path.join(UPLOAD_DIR, stt_id + ".txt"))
        return txt_file_path
    else:
        result = ""
        return result


@app.post("/transcribe/")
async def transcribe(soundfile: UploadFile = File(...)):
    stt_id = str(uuid.uuid4())
    print(f"File: {soundfile.filename!r}")
    #
    audio_file_path, audio_file_size = await save_sound_file(stt_id, soundfile)

    #
    if audio_file_size < 480000:
        transcription_task = celery.send_task("speech_to_text", args=(audio_file_path,))
        task_result = transcription_task.get(timeout=60.0)
        result = task_result
    else:
        result = {
            "id": stt_id,
            "version": 2,
            "success": False,
            "message": "The soundfile was too large. Use 'transcribe_long_form' for longer audio.",
        }

    return result


@app.post("/transcribe_long_form/")
async def transcribe_long_form(request: Request, soundfile: UploadFile = File(...)):
    #
    stt_id = str(uuid.uuid4())

    audio_file_path, audio_file_size = await save_sound_file(stt_id, soundfile)
    transcription_task = celery.send_task("speech_to_text", args=(audio_file_path,))
    tasks.setdefault(stt_id, transcription_task.task_id)

    return {"id": stt_id, "version": 2, "success": True}


@app.post("/queue_transcribe_long_form/")
async def queue_transcribe_long_form(
    request: Request,
    soundfile: UploadFile = File(...),
    consumer: str = Form(...),
    priority: int = Form(...),
):
    #
    stt_id = str(uuid.uuid4())

    audio_file_path, audio_file_size = await save_sound_file(stt_id, soundfile)
    transcripton_job = Job(
        stt_id=stt_id,
        consumer_id=consumer,
        priority=priority,
        callback_url=API_HOST + f"transcribe_long_form_begin/{stt_id}/",
    )

    await addJob(transcripton_job)

    # peidio defnyddio hwn o bosib os am creu endpoint ar wahan i job progress.
    # tasks.setdefault(stt_id, "UNKNOWN")
    #
    # os yw'r galwr yn galw ar get_status, cyn iddo cael ei weithredu o'r callback, yna
    # bydd y task_status yn 'UNKNOWN'. I gwybod os yw'r stt_id yn disgwyl callback yna,
    # rhaid i'r get_status galw ar y Jobs API gateway.
    #

    return {"id": stt_id, "version": 2, "success": True}


########################################################################################
# API methods to support uploading in chunks
#


@app.get("/transcribe_long_form_initiate/")
# @limiter.limit("2/hour")
async def transcribe_long_form_initiate(request: Request):
    stt_id = str(uuid.uuid4())
    return {"id": stt_id, "version": 2, "success": True}


@app.post("/transcribe_long_form_chunk/{stt_id}/")
async def transcribe_long_form_chunk(stt_id: str, request: Request):
    #
    audio_file_path = os.path.join(UPLOAD_DIR, stt_id)

    #
    data = b""
    async for chunk in request.stream():
        data += chunk

    if Path(audio_file_path).is_file():
        async with aiofiles.open(audio_file_path, "ab") as f:
            await f.write(data)
    else:
        async with aiofiles.open(audio_file_path, "wb") as f:
            await f.write(data)

    #
    return {"id": stt_id, "version": 2, "success": True}


@app.get("/transcribe_long_form_begin/{stt_id}/")
async def transcribe_long_form_begin(stt_id: str):
    audio_file_path = get_audio_file_path(stt_id)
    transcription_task = celery.send_task("speech_to_text", args=(audio_file_path,))

    # has no effect if key already exists. But! if the API was restarted,
    # then it's great to be re-added :)
    tasks.setdefault(stt_id, transcription_task.task_id)
    tasks[stt_id] = transcription_task.task_id

    return {
        "id": stt_id,
        "version": 2,
        "success": True,
        "poll_url": API_HOST + f"get_status/?stt_id={stt_id}",
    }


#
########################################################################################


async def save_sound_file(stt_id, soundfile):
    try:
        audio_file_path = os.path.join(UPLOAD_DIR, stt_id)
        data = await soundfile.read()
        async with aiofiles.open(audio_file_path, "wb") as f:
            await f.write(data)
    except Exception as _:
        traceback.print_exc()
    return audio_file_path, os.path.getsize(audio_file_path)


@app.get("/get_json/", response_class=FileResponse)
async def get_json(stt_id):
    json_file_path = Path(os.path.join(UPLOAD_DIR, stt_id + ".json"))
    return json_file_path


@app.get("/get_elan/", response_class=FileResponse)
async def get_elan(stt_id):
    eaf_file_path = Path(os.path.join(UPLOAD_DIR, stt_id + ".eaf"))
    print(eaf_file_path)
    return eaf_file_path


@app.get("/get_srt/", response_class=FileResponse)
async def get_srt(stt_id):
    srt_file_path = Path(os.path.join(UPLOAD_DIR, stt_id + ".srt"))
    return srt_file_path


@app.get("/get_vtt/")
def get_vtt(stt_id):
    vtt_file_path = os.path.join(UPLOAD_DIR, stt_id + ".vtt")
    return FileResponse(path=vtt_file_path, filename=Path(vtt_file_path).name)


@app.get("/get_wav/")
def get_wav(stt_id):
    wav_file_path = os.path.join(UPLOAD_DIR, stt_id + ".wav")
    return FileResponse(path=wav_file_path, filename=Path(wav_file_path).name)


@app.get("/delete/")
async def delete(stt_id, consumer=""):
    result = True
    if "*" in stt_id:
        result = False

    # delete files
    delete_all_files(stt_id=stt_id)

    # delete any pending jobs
    transcripton_job = Job(
        stt_id=stt_id, consumer_id=consumer, callback_url="", priority=0.0
    )
    await cancelJob(transcripton_job)

    #
    return {"id": stt_id, "version": 2, "success": result}
