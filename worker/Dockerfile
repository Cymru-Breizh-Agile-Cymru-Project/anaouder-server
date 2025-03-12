FROM ubuntu:22.04

ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=Europe/London

RUN apt update -q \
   && apt install -y -qq tzdata bash build-essential git curl wget software-properties-common \
   vim ca-certificates libffi-dev libssl-dev libsndfile1 libbz2-dev liblzma-dev locales \
   libboost-all-dev libboost-tools-dev libboost-thread-dev cmake  \
   python3 python3-pip python3-setuptools python3-dev curl zip zlib1g-dev vim \
   ffmpeg sox alsa-utils protobuf-compiler
RUN python3 -m pip install --upgrade pip
RUN apt clean -q


WORKDIR /worker
COPY ./requirements.txt .
RUN pip install -r requirements.txt

COPY . .

RUN pwd && ls -l 

ENTRYPOINT ["./start_workers.sh"]

