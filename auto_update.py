import requests
import time
import subprocess


def get_latest_commit():
    try:
        r = requests.get("https://api.github.com/repos/OfficialFreak/tum-commute-planner/commits/master")
        return r.json()["sha"]
    except Exception as ex:
        print(ex)
        return None


def main():
    print("Starting Auto-Update Script.")
    latest_known_commit = None
    script_process = None
    while 1:
        latest_commit = get_latest_commit()
        if latest_commit != latest_known_commit:
            print("New commit found.")
            if script_process is not None:
                subprocess.Popen.terminate(script_process)
                while subprocess.Popen.poll(script_process) is not None:
                    # Wait until old script has terminated
                    time.sleep(0.25)
            # Refresh Repo
            print("Pulling changes")
            subprocess.run(["git", "pull"])
            print("Restarting Commute Planner")
            script_process = subprocess.Popen(
                [".venv/Scripts/python.exe", "-m", "commute_planner.main"],
                creationflags=subprocess.CREATE_NEW_CONSOLE)
            latest_known_commit = latest_commit
        time.sleep(60 * 1)


if __name__ == "__main__":
    main()
