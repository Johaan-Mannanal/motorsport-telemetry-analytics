"""The local explorer must not silently stop offering recent seasons."""
from datetime import date
from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_live_season_picker_includes_current_year():
    app = AppTest.from_file(str(Path(__file__).parents[1] / "app.py")).run(timeout=30)
    assert not app.exception
    season = next(select for select in app.selectbox if select.label == "Season")
    assert str(date.today().year) in season.options
    assert "2018" in season.options
