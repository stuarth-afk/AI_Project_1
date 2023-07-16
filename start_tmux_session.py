import os

# Start tmux session and run the application
os.system("tmux new-session -d -s mysession 'python3 app.py'")

# Detach from the tmux session
#os.system("tmux detach-client -s mysession")

# Detaching from session can be done manually by
# pressing Ctrl+b followed by d.
