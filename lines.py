
from abc import ABC
from dataclasses import dataclass

from .structures import Change, Condition, NtDefinition, NtFile, Pattern, With

@dataclass
class Line(ABC):
    indent: int

@dataclass
class LineChange(Line):
    """Für bereits vollständig geparste Zeilen"""
    content: Change

@dataclass
class LineCondition(Line):
    """Für bereits vollständig geparste Zeilen"""
    content: Condition

@dataclass
class LineBNPattern(Line):
    """Für bereits vollständig geparste Zeilen"""
    content: Pattern

class LineOpenFrom(Line):
    pass

@dataclass
class LineFullFrom(Line):
    """From-Einzeiler.\n
    Ziemlich sinnlos, aber ok und muss man halt machen"""
    subpattern: Pattern

class LineOpenWith(Line):
    pass

@dataclass
class LineFullWith(Line):
    """With-Einzeiler."""
    changes: With

@dataclass
class LineIf(Line):
    """If-Zeile"""
    condition: Condition

@dataclass
class LineOpenNt(Line):
    name: str
    param_names: set[str]

@dataclass
class LineFullNt(Line):
    """Nt-Einzeiler."""
    name: str
    param_names: set[str]
    subpattern: Pattern
    def to_nt(self) -> NtDefinition:
        return NtDefinition(
            self.name,
            self.param_names,
            self.subpattern
        )

@dataclass
class LineFileNt(Line):
    """NtFile-Einzeiler."""
    name: str
    param_names: set[str]
    filename: str
    def to_nt(self) -> NtFile:
        return NtFile(
            self.name,
            self.param_names,
            self.filename
        )