#! /usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path
import datetime
import json
import srt
from anaouder.asr.dataset import create_eaf


def create_srt(splits: list[list[dict]]):
    max_words_per_line = 7
    subs = []
    for split in splits:
        for j in range(0, len(split), max_words_per_line):
            tokens = split[j : j + max_words_per_line]
            text = " ".join([word["word"] for word in tokens])

            s = srt.Subtitle(
                index=len(subs),
                content=text,
                start=datetime.timedelta(seconds=tokens[0]["start"]),
                end=datetime.timedelta(seconds=tokens[-1]["end"]),
            )
            subs.append(s)
    return srt.compose(subs)


def convert_from_json(json_path: Path, max_time_gap=0.6):
    """
    Converts json data to different formats

    Args:
        max_time_gap: float
            The maximum time gap between two tokens
            before the stream of tokens is splitted
    """
    json_data = json.loads(json_path.read_text())

    splits = []
    split = [json_data[0]]
    for token in json_data[1:]:
        last_token_end = split[-1]["end"]
        if token["start"] - last_token_end > max_time_gap:
            # Split token stream at this point
            splits.append(split)
            split = [token]
        else:
            split.append(token)
    if split:
        splits.append(split)

    sentences = [" ".join([token["word"] for token in split]) for split in splits]

    segments = [(tokens[0]["start"], tokens[-1]["end"]) for tokens in splits]
    eaf_file_path = json_path.with_suffix(".eaf")

    return {
        "json": json_data,
        "txt": "\n".join(sentences),
        "eaf": create_eaf(segments, sentences, eaf_file_path),
        "srt": create_srt(splits),
    }
