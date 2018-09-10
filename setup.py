import sys
from cx_Freeze import setup, Executable

base = None

if sys.platform == "win32":
    base = "Win32GUI"

executables = [Executable("uploader_app.py", base=base)]

packages = ["idna"]
options = {
    'build_exe': {
        'packages': packages,
    },
}

setup(
    name="Youtube uploader",
    options=options,
    version="0.1",
    description='',
    executables=executables
)
