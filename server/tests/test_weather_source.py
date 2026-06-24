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
