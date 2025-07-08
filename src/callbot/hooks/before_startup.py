from dataclasses import dataclass

from fastapi import FastAPI

from .hook import Hook


@dataclass
class BeforeStartupHook(Hook):
    app: FastAPI
