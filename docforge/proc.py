import subprocess
import sys

# subprocess flag: don't flash a console window when running under pythonw
# (GUI without a terminal). The flag doesn't exist off Windows — use 0 there.
NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
