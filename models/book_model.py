import logging
from typing import Any, List

class Book:
    id: int
    title: str

    def __init__(self, id: int, title: str):
        self.id = id
        self.title = title
    #enddef

    