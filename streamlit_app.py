"""Streamlit Cloud entrypoint.

The hosted app lives in app.py. Its UI is built inside app.main() guarded by
`if __name__ == "__main__"`, so a bare `import app` runs nothing and the page
renders blank. Call main() explicitly so the app renders under any entrypoint.
"""

from app import main

main()
