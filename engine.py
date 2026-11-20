from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Event
import requests

from config import BOT_TOKEN, CHAT_ID, WORKERS

stop_event = Event()

PHOTO_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".webp"
}

def stop_backup():
    stop_event.set()


def find_photos():
    list_file = Path(__file__).parent / "selected_photos.txt"

    if not list_file.exists():
        raise RuntimeError(
            "selected_photos.txt not found."
        )

    photos = []

    for line in list_file.read_text().splitlines():
        path = Path(line.strip()).expanduser()

        if (
            path.is_file()
            and path.suffix.lower() in PHOTO_EXTENSIONS
        ):
            photos.append(path)

    return list(dict.fromkeys(photos))


def upload_one(path):
    if stop_event.is_set():
        return "stopped"

    url = (
        f"https://api.telegram.org/"
        f"bot{BOT_TOKEN}/sendDocument"
    )

    try:
        with path.open("rb") as photo:
            response = requests.post(
                url,
                data={"chat_id": CHAT_ID},
                files={
                    "document": (path.name, photo)
                },
                timeout=(15, 180)
            )

        data = response.json()

        if response.ok and data.get("ok"):
            return "success"

        return "failed"

    except Exception:
        return "failed"


def start_backup(on_progress=None):
    if BOT_TOKEN == "YOUR_BOT_TOKEN":
        raise RuntimeError("Configure BOT_TOKEN first.")

    if CHAT_ID == "YOUR_CHAT_ID":
        raise RuntimeError("Configure CHAT_ID first.")

    stop_event.clear()

    photos = find_photos()

    success = 0
    failed = 0
    stopped = 0
    completed = 0

    with ThreadPoolExecutor(
        max_workers=WORKERS
    ) as pool:

        futures = [
            pool.submit(upload_one, photo)
            for photo in photos
        ]

        for future in as_completed(futures):
            result = future.result()
            completed += 1

            if result == "success":
                success += 1
            elif result == "failed":
                failed += 1
            else:
                stopped += 1

            if on_progress:
                on_progress(
                    completed,
                    len(photos),
                    success,
                    failed
                )

    return {
        "total": len(photos),
        "success": success,
        "failed": failed,
        "stopped": stopped
    }