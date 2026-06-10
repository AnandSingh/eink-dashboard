"""Meta AI glasses integration — kept separate from the core dashboard.

Everything Meta-glasses-specific lives here: the photo-capture pipeline
(watcher → classifier → router → extractors) and the voice write-back bot.
The core (config, store, renderer, widgets, api) is integration-agnostic and
does not import from this package, so the glasses integration can be swapped
or removed without touching the dashboard itself.
"""
