import sys
import os
import streamlit.web.bootstrap
# Simulate loading the module
try:
    import backend.chat_engine
    print("chat_engine imported fine")
except Exception as e:
    print(f"Error in chat_engine: {e}")
    sys.exit(1)

try:
    import frontend.app
    print("app.py imported fine")
except Exception as e:
    import traceback
    traceback.print_exc()
    sys.exit(1)
