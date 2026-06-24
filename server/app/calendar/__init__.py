"""Calendar integration — optional, removable, like glasses/.

Fetches a single personal .ics, expands recurrences, and deposits events into
the core store. The core (renderer/store/config/widgets) never imports this
package; wiring lives only in app/main.py.
"""
