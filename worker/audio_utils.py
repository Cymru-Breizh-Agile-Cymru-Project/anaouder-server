import shlex
import subprocess

from pathlib import Path


def prepare_audio(audio_file_path) -> Path:
    print("Task prepare_audio for %s started" % audio_file_path)

    wav_file_path=convert_audio(audio_file_path)
    wav_normalized_audio_file_path = normalize_audio(wav_file_path)

    print ("Completed prepared audio file : %s" % wav_normalized_audio_file_path)
    return Path(wav_normalized_audio_file_path)


def convert_audio(audio_file_path):
    print ("Converting to viable wav...")

    wav_file_path = Path(audio_file_path).with_suffix(".wav")

    original_audio_file = Path(audio_file_path)
    original_audio_file_path = original_audio_file.with_name("original_" + original_audio_file.name + original_audio_file.suffix)
    original_audio_file.rename(original_audio_file_path)

    convert_cmd = "ffmpeg -i {} -vn -acodec pcm_s16le -ar 16000 -ac 1 {}".format(original_audio_file_path, wav_file_path)
    subprocess.Popen(shlex.split(convert_cmd)).wait()

    Path(original_audio_file_path).unlink()

    return wav_file_path.as_posix()


def normalize_audio(wav_file_path):
    wav_file_path = Path(wav_file_path)
    wav_normalized_file_path = Path(wav_file_path).with_suffix(".n.wav")
                                                                                    
    normalize_cmd = "ffmpeg-normalize {} -ar 16000 -o {}".format(wav_file_path, wav_normalized_file_path)
    subprocess.Popen(shlex.split(normalize_cmd)).wait()
                                                                                                
    wav_file_path.unlink()
    wav_file_path = wav_normalized_file_path.rename(wav_file_path.with_suffix(".wav").as_posix())
                                                                                                            
    return wav_file_path.as_posix()

