"""HTML rendering: the configured Jinja2 environment.

Lives in its own module so routers and app.main can both import it without
importing each other. Custom filters and globals belong here too.
"""

from pathlib import Path

from fastapi.templating import Jinja2Templates

TEMPLATES_DIR = Path(__file__).parent / "templates"

templates = Jinja2Templates(directory=TEMPLATES_DIR)
