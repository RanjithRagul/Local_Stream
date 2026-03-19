my_token = "" # get it from src
torrent_input = r"" # env 

import requests
from seedrcc import Seedr, Token
import time
import os


FETCH_TIMEOUT = 120  # 2 minutes


def clear_seedr_storage(seed):
    drive = seed.list_contents()

    for folder in drive.folders:
        try:
            seed.delete_folder(folder.id)
        except:
            pass

    for file in drive.files:
        try:
            seed.delete_file(file.folder_file_id)
        except:
            pass


def wait_for_fetch(seed):
    start_time = time.time()

    while True:
        if time.time() - start_time > FETCH_TIMEOUT:
            return None, None

        drive = seed.list_contents()

        # Multi-file (folder case)
        if drive.folders:
            folder = drive.folders[0]
            folder_content = seed.list_contents(folder.id)

            if folder_content.files:
                return folder, folder_content.files

        # Single-file case
        if drive.files:
            return None, drive.files

        time.sleep(5)


def download_with_resume(url, filepath, total_size):
    existing_size = 0

    if os.path.exists(filepath):
        existing_size = os.path.getsize(filepath)

    headers = {}
    if existing_size > 0:
        headers["Range"] = f"bytes={existing_size}-"

    downloaded = existing_size

    while downloaded < total_size:
        try:
            response = requests.get(url, headers=headers, stream=True, timeout=30)
            mode = "ab" if downloaded > 0 else "wb"

            with open(filepath, mode) as f:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

                        percent = (downloaded / total_size) * 100
                        remaining = (total_size - downloaded) / (1024 * 1024)

                        print(
                            # f"\r{os.path.basename(filepath)} | "
                            f"{percent:.2f}% | "
                            f"Left: {remaining:.2f} MB",
                            end=""
                        )

            break

        except requests.exceptions.RequestException:
            print(f"\nConnection lost. Resuming {os.path.basename(filepath)}...")
            time.sleep(3)
            existing_size = os.path.getsize(filepath)
            headers["Range"] = f"bytes={existing_size}-"
            downloaded = existing_size

    print()


def start_download():
    token_obj = Token(access_token=my_token)
    seed = Seedr(token=token_obj)

    print("Cleaning Seedr storage...")
    clear_seedr_storage(seed)

    print("Adding torrent...")
    try:
        seed.add_torrent(torrent_input)
    except Exception as e:
        print("Failed to add torrent.")
        print(e)
        return

    print("Waiting for cloud fetch (max 2 min)...")

    folder, files = wait_for_fetch(seed)

    if not files:
        print("Peers not available or fetch timeout.")
        clear_seedr_storage(seed)
        return

    # Create local folder if multi-file
    if folder:
        local_folder = folder.name.replace(" ", "_")
        os.makedirs(local_folder, exist_ok=True)
    else:
        local_folder = None

    for file in files:
        file_id = file.folder_file_id
        file_details = seed.fetch_file(file_id)
        download_url = file_details.url

        filename = file.name.replace(" ", "_")

        if local_folder:
            filepath = os.path.join(local_folder, filename)
        else:
            filepath = filename

        total_size = int(file.size)

        print(f"Downloading: {filename}")
        download_with_resume(download_url, filepath, total_size)

    print("Download complete.")

    clear_seedr_storage(seed)


if __name__ == "__main__":
    start_download()
