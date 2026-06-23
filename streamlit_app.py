"""Streamlit Cloud entrypoint.

The hosted app lives in app.py. This wrapper gives Streamlit Cloud a stable
entrypoint without changing the local app path.
"""

import app  # noqa: F401
