"""Weather integration — optional, removable, like glasses/ and calendar/.

Resolves a location (manual override or IP geolocation) and fetches current
conditions + today's high/low from Open-Meteo, depositing a snapshot in the core
store (meta['weather']). The core never imports this package; wiring lives only
in app/main.py.
"""
