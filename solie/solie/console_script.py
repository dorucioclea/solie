import os
import subprocess
import sys


def start():
    python_interpreter = sys.executable
    if os.name == "nt":
        python_interpreter = os.path.join(
            os.path.dirname(python_interpreter),
            "pythonw.exe",
        )
        command = [python_interpreter, "-m", "solie"]
        subprocess.Popen(
            command,
            creationflags=subprocess.DETACHED_PROCESS,
        )
    else:
        command = ["nohup", python_interpreter, "-m", "solie"]
        subprocess.Popen(
            command,
            preexec_fn=os.setpgrp,
        )
