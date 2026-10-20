import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

OWNER = "donobangg"
REPO = "contextmesh-test"
BRANCH = "main"
CHECK_INTERVAL = 120  # Seconds

OUTPUT = Path(__file__).with_name("repo_context.json")


def fetch_latest_commit():
    branch = quote(BRANCH, safe="")
    url = f"https://api.github.com/repos/{OWNER}/{REPO}/commits/{branch}"
    request = Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "ContextMesh-Test",
        },
    )

    with urlopen(request, timeout=20) as response:
        return json.load(response)


def save_context(commit):
    context = {
        "repository": f"{OWNER}/{REPO}",
        "branch": BRANCH,
        "commit_sha": commit["sha"],
        "commit_message": commit["commit"]["message"],
        "commit_url": commit["html_url"],
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "changed_files": [
            {
                "path": file["filename"],
                "status": file["status"],
                "patch": file.get("patch"),
            }
            for file in commit.get("files", [])
        ],
    }

    OUTPUT.write_text(
        json.dumps(context, indent=2),
        encoding="utf-8",
    )
    return context


def main():
    previous_sha = None
    print(f"Watching {OWNER}/{REPO}, branch {BRANCH}")
    print("Keep this terminal open. Press Ctrl+C to stop.")

    while True:
        try:
            commit = fetch_latest_commit()

            if commit["sha"] != previous_sha:
                context = save_context(commit)

                label = (
                    "Initial snapshot saved"
                    if previous_sha is None
                    else "Repository update detected"
                )
                print(f"\n{label}: {context['commit_sha'][:7]}")
                print(context["commit_message"])
                for file in context["changed_files"]:
                    print(f"  {file['status']}: {file['path']}")
                print(f"Context saved to {OUTPUT.name}")

                previous_sha = commit["sha"]
            else:
                print("No new commit.")

        except HTTPError as error:
            print(f"GitHub returned HTTP {error.code}.")
            if error.code in (403, 429):
                print("Access or rate-limit issue. Stop and check before retrying.")
                break
            if error.code == 404:
                print("Check the username, repository, branch, and public visibility.")
                break
        except (URLError, TimeoutError) as error:
            print(f"Connection problem: {error}")

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nWatcher stopped.")