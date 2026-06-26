"""Tests for the core weather display helpers (pure, no network)."""
import json

from app import weathericons, weatherview


def test_category_buckets():
    assert weathericons.category(0) == "clear"
    assert weathericons.category(1) == "partly"
    assert weathericons.category(2) == "partly"
    assert weathericons.category(3) == "cloudy"
    assert weathericons.category(45) == "cloudy"
    assert weathericons.category(51) == "rain"
    assert weathericons.category(56) == "rain"   # freezing drizzle in range
    assert weathericons.category(65) == "rain"
    assert weathericons.category(67) == "rain"   # freezing rain in range
    assert weathericons.category(80) == "rain"
    assert weathericons.category(71) == "snow"
    assert weathericons.category(86) == "snow"
    assert weathericons.category(95) == "thunder"
    assert weathericons.category(99) == "thunder"


def test_category_unknown_defaults_cloudy():
    assert weathericons.category(1234) == "cloudy"
    assert weathericons.category(-1) == "cloudy"


def test_view_parse_valid():
    blob = json.dumps({"temp": 71.6, "high": 78.2, "low": 60.9, "code": 1, "city": "X"})
    v = weatherview.parse(blob)
    assert v == {"temp_txt": "72°", "hl_txt": "H78 L61", "code": 1}


def test_view_parse_missing_or_garbage():
    assert weatherview.parse(None) is None
    assert weatherview.parse("") is None
    assert weatherview.parse("not json") is None
    assert weatherview.parse(json.dumps({"temp": 70, "high": 75})) is None  # no low/code
    assert weatherview.parse(json.dumps({"temp": "warm", "high": 75, "low": 60, "code": 0})) is None
    assert weatherview.parse(json.dumps({"temp": 70, "high": 75, "low": 60, "code": "1"})) is None


def test_view_parse_rejects_bool_temp():
    # bool is an int subclass — must not be accepted as a temperature
    assert weatherview.parse(json.dumps({"temp": True, "high": 75, "low": 60, "code": 0})) is None


def test_parse_sun_valid():
    blob = json.dumps({"temp": 70, "high": 75, "low": 60, "code": 1,
                       "sunrise": "2026-06-28T05:14", "sunset": "2026-06-28T21:10",
                       "utc_offset": -25200})
    assert weatherview.parse_sun(blob) == {
        "sunrise": "2026-06-28T05:14", "sunset": "2026-06-28T21:10", "utc_offset": -25200,
    }


def test_parse_sun_absent_or_garbage():
    assert weatherview.parse_sun(None) is None
    assert weatherview.parse_sun("not json") is None
    # core weather present but no sun fields -> None (header still works via parse())
    assert weatherview.parse_sun(json.dumps({"temp": 70, "high": 75, "low": 60, "code": 1})) is None
    # missing offset defaults to 0
    blob = json.dumps({"sunrise": "2026-06-28T05:14", "sunset": "2026-06-28T21:10"})
    assert weatherview.parse_sun(blob)["utc_offset"] == 0


def test_draw_glyphs_do_not_raise():
    from PIL import Image, ImageDraw
    img = Image.new("L", (60, 60), color=255)
    d = ImageDraw.Draw(img)
    for code in (0, 1, 3, 51, 71, 95, 9999):
        weathericons.draw(d, (10, 10, 40, 40), code)
