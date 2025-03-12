from pathlib import Path

from anaouder.asr.models import _download, get_latest_model
from celery import Task


class SpeechToTextTask(Task):
    """
    Abstraction of Celery's Task class to support loading ML model.
    """

    abstract = True

    def __init__(self):
        super().__init__()
        model_path = Path("/models") / get_latest_model()
        if not model_path.exists():
            _download(get_latest_model(), "/models")

    def __call__(self, *args, **kwargs):
        """
        Load model on first call (i.e. first task processed)
        Avoids the need to load model on each task request
        """
        return self.run(*args, **kwargs)
