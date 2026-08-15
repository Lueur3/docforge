import subprocess
import sys

# Флаг для subprocess: не показывать окно консоли при запуске из pythonw
# (GUI без терминала). На не-Windows флага нет — значение 0.
NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
