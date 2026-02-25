import pytest

from src.consolidator.aligner import Aligner


def test_align_returns_list_of_consolidated_records():
    aligner = Aligner()
    # TODO: provide realistic stub inputs
    with pytest.raises(NotImplementedError):
        aligner.align([], [], [])


def test_flag_inconsistencies_raises():
    aligner = Aligner()
    with pytest.raises(NotImplementedError):
        aligner.flag_inconsistencies([])
