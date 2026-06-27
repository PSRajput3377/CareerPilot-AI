"""Email Template Engine package (Module 10).

Re-exports the renderer, the built-in template seeds, and the service.
"""

from careerpilot.backend.services.templating.builtins import BUILTIN_TEMPLATES
from careerpilot.backend.services.templating.renderer import (
    TemplateRenderError,
    extract_placeholders,
    render_template,
)
from careerpilot.backend.services.templating.service import EmailTemplateService

__all__ = [
    "BUILTIN_TEMPLATES",
    "TemplateRenderError",
    "extract_placeholders",
    "render_template",
    "EmailTemplateService",
]
