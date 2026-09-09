from dataclasses import dataclass


@dataclass(frozen=True)
class ScrutinyNoteRequestDTO:
    thread_id: str


@dataclass(frozen=True)
class ScrutinyNoteDTO:
    thread_id: str
    text: str
