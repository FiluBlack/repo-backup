"""The web application.

Layered so each part can be read and tested on its own:

    settings.py   configuration, read from the environment
    providers.py  objects FastAPI injects into routes
    rendering.py  the Jinja2 environment
    main.py       assembly — creates the app and wires the pieces together

    routers/      the HTTP surface
    schemas/      the shapes that cross the wire
    services/     the work itself, free of FastAPI

Requests flow inward: a router validates input, calls a service, and returns
either a rendered template or a schema. Services never import upward.
"""
