#!/bin/bash
celery -A tasks worker --pool solo --loglevel=info -n kaldi_stt_worker_1
