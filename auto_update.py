# I advise against using this as it automatically downloads and runs code from this repository
import os

import requests
import time
import subprocess

from dotenv import load_dotenv


def get_latest_commit():
    try:
        r = requests.get("https://api.github.com/repos/OfficialFreak/tum-commute-planner/commits/master")
        return r.json()["sha"]
    except Exception as ex:
        return None


def main():
    print("Starting Auto-Update Script.")
    latest_known_commit = None
    script_process = None
    try:
        while 1:
            latest_commit = get_latest_commit()
            if latest_commit != latest_known_commit:
                print("New commit found.")
                if script_process is not None:
                    subprocess.Popen.terminate(script_process)
                # Refresh Repo
                print("Pulling changes")
                subprocess.run(["git", "pull"])
                print("Restarting Commute Planner")
                # script_process = subprocess.Popen([
                #   os.environ.get("VENV_PYTHON_EXECUTABLE"), "-m", "commute_planner.main"])
                script_process = subprocess.Popen([
                    os.environ.get("VENV_PYTHON_EXECUTABLE"), "phue_connected_commute_planner.py"])
                latest_known_commit = latest_commit
            time.sleep(60 * 1)
    except KeyboardInterrupt:
        print("Shutting down...")
        if script_process is not None:
            subprocess.Popen.terminate(script_process)


if __name__ == "__main__":
    load_dotenv()
    main()
