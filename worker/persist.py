import json
import pympi
import srt
import webvtt

from pathlib import Path
from datetime import timedelta

import xml.etree.ElementTree as et

def save_as_json(audio_file_path, transcription):
    json_str = json.dumps(transcription)
    json_file_path = Path(audio_file_path).with_suffix(".json")
    with open(json_file_path, 'w', encoding='utf-8') as json_file:
        json_file.write(json_str)
    return json_file_path


def save_as_text(audio_file_path, transcription):
    text = ''

    for transcript in transcription["segments"]:
        text = text + transcript["text"].strip()
        if text.endswith("."): 
            text = text + " "

    text = text.strip()

    text_file_path = Path(audio_file_path).with_suffix(".txt")
    with open(text_file_path, 'w', encoding='utf-8') as text_file:
        text_file.write(text)

    return text_file_path


def save_as_srt(audio_file_path, transcription):
    i = 0

    srt_segments = []
    srt_file_path = Path(audio_file_path).with_suffix(".srt")
    
    for transcript in transcription["segments"]:
        i = i+1
        if "start" in transcript and "end" in transcript and "text" in transcript:
            time_start = transcript["start"]
            time_end = transcript["end"]
            if time_start == time_end:
                continue

            text = transcript["text"]
            
            start_delta = timedelta(seconds=time_start)
            end_delta = timedelta(seconds=time_end)
            srt_segments.append(srt.Subtitle(i, start=start_delta, end=end_delta, content=text))

    srt_string = srt.compose(srt_segments)

    with open(srt_file_path, 'w', encoding='utf-8') as srt_file:
        srt_file.write(srt_string)
    
    print("srt file of transcription saved to %s" % srt_file_path)

    return srt_file_path


def save_as_elan(audio_file_path, transcription):
    
    i=0
    
    #
    output_eaf=pympi.Elan.Eaf()

    audio_file = Path(audio_file_path)
    output_eaf.add_linked_file("get_audio?stt_id=" + audio_file.stem, mimetype="wav")

    output_eaf.add_tier('EDU')
    output_eaf.add_tier('EDU_W2V2')
    
    output_eaf.add_tier('Text')
    output_eaf.add_tier('Wav2Vec2')
    #
    for transcript in transcription["segments"]:
        i = i+1
        if "start" in transcript and "end" in transcript:
            time_start = int(transcript["start"] * 1000)
            time_end = int(transcript["end"] * 1000)
           
            # ELAN.py raises ValueError exception if the segment is of length zero
            if time_start == time_end:
                continue

            if time_start > time_end:
                continue

            text = transcript["text"]
            output_eaf.insert_annotation('EDU', time_start, time_end, value=str(i))
            output_eaf.insert_ref_annotation('Text','EDU',time=time_start, value=text)

    #
    eaf_file_path = Path(audio_file_path).with_suffix(".eaf")
    output_eaf.to_file(eaf_file_path)

    # pympi deesn't note that timings are in milliseconds in the HEADER.
    eaf_xml = et.parse(eaf_file_path)
    eaf_xml = eaf_xml.getroot()
    h = eaf_xml.find(".//HEADER")
    h.set('TIME_UNITS', 'milliseconds')
    with open(eaf_file_path, 'wb') as eaf_file:
        eaf_file.write(et.tostring(eaf_xml))


def save_as_vtt(audio_file_path, transcription):
    # we'll use the srt file
    srt_file_path = Path(audio_file_path).with_suffix(".srt")
    if not Path(srt_file_path).is_file():
        save_as_srt(audio_file_path=audio_file_path, transcription=transcription)

    vtt_file_path = Path(audio_file_path).with_suffix(".vtt")
    try:
        webvtt.from_srt(srt_file_path).save(output=vtt_file_path)
    except:
        with open(vtt_file_path, 'w') as vtt_file: pass

