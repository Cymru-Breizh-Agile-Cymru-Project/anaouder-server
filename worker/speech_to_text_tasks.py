from celery import Task


from anaouder.asr.models import _download, _get_model_directory, get_latest_model

class SpeechToTextTask(Task):
    """
    Abstraction of Celery's Task class to support loading ML model.
    """

    abstract = True

    def __init__(self):
        super().__init__()
        _download(get_latest_model(), _get_model_directory())

    def __call__(self, *args, **kwargs):
        """
        Load model on first call (i.e. first task processed)
        Avoids the need to load model on each task request
        """
        return self.run(*args, **kwargs)
