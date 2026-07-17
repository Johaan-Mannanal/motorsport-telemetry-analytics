"""Tests for the bundled offline sample sessions."""
import pytest

from src import sample_data as sd
from src import data_loader as dl


def test_samples_are_listed():
    samples = sd.list_samples()
    assert len(samples) >= 1
    assert all("slug" in s and "label" in s for s in samples)


def test_load_sample_and_accessors():
    slug = sd.list_samples()[0]["slug"]
    sess = sd.load_sample(slug)
    drivers = dl.session_drivers(sess)
    assert len(drivers) >= 2
    a, b = drivers[0], drivers[1]
    tel = dl.fastest_car_telemetry(sess, a)
    assert {"Distance", "Speed"}.issubset(tel.columns) and len(tel) > 0
    pos = dl.fastest_position(sess, a)
    assert {"X", "Y"}.issubset(pos.columns)
    assert dl.fastest_lap_row(sess, b) is not None
    assert not dl.session_laps(sess).empty


def test_missing_sample_raises():
    with pytest.raises(FileNotFoundError):
        sd.load_sample("does-not-exist")
