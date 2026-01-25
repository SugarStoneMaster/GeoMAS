"""
Web Views Package.

Tab view modules for the Streamlit dashboard.
"""

from web.views.map_page import render_map_page
from web.views.logs_page import render_logs_page
from web.views.deception_page import render_deception_page

__all__ = [
    "render_map_page",
    "render_logs_page", 
    "render_deception_page"
]
