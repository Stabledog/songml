"""Shared test fixtures for songml-utils tests."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

import pytest


@dataclass
class FakeChordToken:
    """Fake chord token for testing."""

    text: str
    start_beat: float = 1.0
    duration_beats: float = 1.0


@dataclass
class FakeBar:
    """Fake bar for testing."""

    number: int
    line_number: int
    chords: list[FakeChordToken] = field(default_factory=list)


@dataclass
class FakeSection:
    """Fake section for testing."""

    name: str
    bars: list[FakeBar] = field(default_factory=list)


@dataclass
class FakeDoc:
    """Fake parsed document for testing."""

    items: list[Any] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_json(self) -> str:
        """Return minimal JSON representation."""
        return json.dumps({"items": len(self.items), "warnings": self.warnings})


@pytest.fixture
def sample_doc() -> FakeDoc:
    """Provide a minimal fake parsed document."""
    bar1 = FakeBar(number=1, line_number=1)
    bar1.chords = [FakeChordToken(text="C"), FakeChordToken(text="G")]

    section = FakeSection(name="Verse", bars=[bar1])

    doc = FakeDoc(items=[section], warnings=[])
    return doc


@pytest.fixture
def sample_doc_with_warnings() -> FakeDoc:
    """Provide a fake parsed document with warnings."""
    bar1 = FakeBar(number=1, line_number=1)
    bar1.chords = [FakeChordToken(text="C")]

    section = FakeSection(name="Intro", bars=[bar1])

    doc = FakeDoc(
        items=[section],
        warnings=["Validation warning 1", "Validation warning 2"],
    )
    return doc
