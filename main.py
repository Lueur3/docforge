"""DocForge entry point — thin launcher (started by DocForge.bat)."""
import os
import sys
import warnings

# pydub warns about ffmpeg missing from PATH at import time — before we get to
# point it at the binary. The warning is bogus; silence it before the import.
warnings.filterwarnings("ignore", message="Couldn't find ffmpeg or avconv")

# Force UTF-8 before any heavy imports
os.environ["PYTHONUTF8"] = "1"
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from docforge.app import main

if __name__ == "__main__":
    main()
