"""The application's actual work.

Modules here import nothing from FastAPI, so they can be called from a route,
a test, or a script without a request in hand. Routers depend on services;
services never depend on routers.

This is the layer worth protecting — it outlives whichever web framework sits
in front of it.
"""
