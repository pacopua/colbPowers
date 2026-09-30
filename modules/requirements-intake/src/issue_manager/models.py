from dataclasses import dataclass, field
from typing import List, Literal

@dataclass
class Instance:
    hash: str
    state: Literal["start", "transcribing", "transcribed", "generated"]
    transcription: str

@dataclass
class Project:
    name: str
    instances: List[Instance] = field(default_factory=list)

@dataclass
class Client:
    name: str
    projects: List[Project] = field(default_factory=list)


