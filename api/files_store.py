import os
import glob

import aiofiles

from pathlib import Path

#
UPLOAD_DIR = "/recordings"

def get_audio_file_path(stt_id):
    return os.path.join(UPLOAD_DIR, stt_id)

def get_file_path(stt_id, extension):
    return os.path.join(UPLOAD_DIR, stt_id + "." + extension)

def get_if_exists_file_path(stt_id, extension):
    p=os.path.join(UPLOAD_DIR, stt_id + "." + extension)
    if not Path(p).is_file():
        return ""
    return p


async def save_sound_file(stt_id, soundfile):
    try:
        audio_file_path = get_audio_file_path(stt_id) 
        data = await soundfile.read()
        async with aiofiles.open(audio_file_path, 'wb') as f:
            await f.write(data)
    except Exception as exc:
        exc.print_exc()
    return audio_file_path, os.path.getsize(audio_file_path)


async def append_data_chunk(stt_id, data):
    audio_file_path = get_audio_file_path(stt_id)
    if Path(audio_file_path).is_file():
        async with aiofiles.open(audio_file_path, 'ab') as f:
            await f.write(data)
    else:
        async with aiofiles.open(audio_file_path, 'wb') as f:
            await f.write(data)


async def delete_all_files(stt_id):
    for f in glob.glob(os.path.join(UPLOAD_DIR, stt_id + "*")):
        os.remove(f)
