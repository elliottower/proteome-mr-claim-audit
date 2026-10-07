import pytest

import run_extraction as rx
import run_extraction_luna as luna
import run_extraction_luna_workers as lw


def test_the_luna_runner_runs_with_the_requested_pool_size(monkeypatch):
    seen = []
    monkeypatch.setattr(rx, "WORKERS", 6)
    monkeypatch.setattr(luna, "main", lambda: seen.append(rx.WORKERS))
    monkeypatch.setenv("LUNA_WORKERS", "24")
    lw.main()
    assert seen == [24]


def test_the_default_applies_without_the_variable(monkeypatch):
    monkeypatch.delenv("LUNA_WORKERS", raising=False)
    assert lw.workers_from_environment() == lw.DEFAULT_WORKERS


@pytest.mark.parametrize("value", ["0", "65", "-3"])
def test_a_number_outside_the_range_is_refused(monkeypatch, value):
    monkeypatch.setenv("LUNA_WORKERS", value)
    with pytest.raises(lw.WorkersError):
        lw.workers_from_environment()
