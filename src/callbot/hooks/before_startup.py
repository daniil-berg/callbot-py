from fastapi import FastAPI

from .hook import Hook


class BeforeStartupHook(Hook):
    def __init__(self, app: FastAPI) -> None:
        self.app = app
