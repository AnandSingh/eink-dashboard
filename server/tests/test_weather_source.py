"""Pure parser tests for the weather source — no network."""
from app.weather import source


def test_parse_ipapi_success():
    d = {"status": "success", "lat": 47.6, "lon": -122.3, "city": "Seattle"}
    assert source.parse_ipapi(d) == {"lat": 47.6, "lon": -122.3, "city": "Seattle"}


def test_parse_ipapi_failure_status():
    assert source.parse_ipapi({"status": "fail", "message": "private range"}) is None
    assert source.parse_ipapi({}) is None
    assert source.parse_ipapi({"status": "success", "lat": None, "lon": 1}) is None


def test_parse_forecast_valid():
    d = {
        "current": {"temperature_2m": 71.4, "weather_code": 2},
        "daily": {"temperature_2m_max": [78.1, 80.0], "temperature_2m_min": [60.2, 59.0]},
    }
    assert source.parse_forecast(d) == {"temp": 71.4, "high": 78.1, "low": 60.2, "code": 2}


def test_parse_forecast_includes_sun_when_present():
    d = {
        "current": {"temperature_2m": 71.4, "weather_code": 2},
        "utc_offset_seconds": -25200,
        "daily": {
            "temperature_2m_max": [78.1], "temperature_2m_min": [60.2],
            "sunrise": ["2026-06-28T05:14"], "sunset": ["2026-06-28T21:10"],
        },
    }
    out = source.parse_forecast(d)
    assert out["sunrise"] == "2026-06-28T05:14"
    assert out["sunset"] == "2026-06-28T21:10"
    assert out["utc_offset"] == -25200


def test_parse_forecast_sun_optional():
    # No sunrise/sunset arrays -> core weather still parses, sun keys absent.
    d = {
        "current": {"temperature_2m": 71.4, "weather_code": 2},
        "daily": {"temperature_2m_max": [78.1], "temperature_2m_min": [60.2]},
    }
    out = source.parse_forecast(d)
    assert out == {"temp": 71.4, "high": 78.1, "low": 60.2, "code": 2}
    # polar / null sun values -> skipped, no crash
    d["daily"]["sunrise"] = [None]
    d["daily"]["sunset"] = [None]
    assert "sunrise" not in source.parse_forecast(d)


def test_parse_forecast_defensive():
    # missing current temp
    assert source.parse_forecast({"current": {"weather_code": 1},
                                  "daily": {"temperature_2m_max": [70], "temperature_2m_min": [50]}}) is None
    # empty daily arrays -> no [0] crash, returns None
    assert source.parse_forecast({"current": {"temperature_2m": 70, "weather_code": 1},
                                  "daily": {"temperature_2m_max": [], "temperature_2m_min": []}}) is None
    # code missing / non-int
    assert source.parse_forecast({"current": {"temperature_2m": 70, "weather_code": "1"},
                                  "daily": {"temperature_2m_max": [70], "temperature_2m_min": [50]}}) is None
    # totally wrong shape
    assert source.parse_forecast([]) is None
    assert source.parse_forecast({}) is None
