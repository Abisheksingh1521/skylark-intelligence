import os
import sys
import subprocess

def main():
    app_path = os.path.join(os.path.dirname(__file__), "app.py")
    cmd = [sys.executable, "-m", "streamlit", "run", app_path, "--server.port=8501", "--server.headless=true"]
    print("Launching Skylark Intelligence Dashboard on http://localhost:8501 ...")
    subprocess.run(cmd)

if __name__ == "__main__":
    main()
