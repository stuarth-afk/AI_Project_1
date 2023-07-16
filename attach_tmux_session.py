import subprocess

# Attach to the existing tmux session
subprocess.call(["tmux", "attach-session", "-t", "mysession"])
