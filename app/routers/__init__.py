"""HTTP routes, grouped by what they return.

Each module exposes a `router` (an APIRouter) that app.main includes:

    pages.py  HTML for a browser, rendered from templates/
    api.py    JSON under /api, described in /docs

Routers parse and validate the request, then hand off to services/. Keeping
the two response kinds apart matters because they fail differently — a broken
page should render an error page, a broken API call should return a JSON body.
"""
