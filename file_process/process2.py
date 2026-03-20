import os
import time
import requests
import subprocess
import oci
from datetime import datetime
from dotenv import load_dotenv
from seedrcc import Seedr, Token

load_dotenv()

class MediaPipeline:
    def __init__(self):
        self.seedr_token = os.getenv("seedr_token")
        self.oci_config = {
            "user": os.getenv("OCI_USER_OCID"),
            "key_content": os.getenv("OCI_PRIVATE_KEY"),
            "fingerprint": os.getenv("OCI_FINGERPRINT"),
            "tenancy": os.getenv("OCI_TENANCY_OCID"),
            "region": os.getenv("OCI_REGION", "us-ashburn-1")
        }
        self.namespace = os.getenv("OCI_NAMESPACE")
        self.bucket = os.getenv("OCI_BUCKET_NAME")

    def clear_seedr_storage(self, seed):
        """Your original cleanup logic."""
        print("Cleaning Seedr storage...")
        drive = seed.list_contents()
        for folder in drive.folders:
            try: seed.delete_folder(folder.id)
            except: pass
        for file in drive.files:
            try: seed.delete_file(file.folder_file_id)
            except: pass

    def download_with_resume(self, url, filepath, total_size):
        """Your original resume-capable downloader."""
        print(filepath)
        existing_size = os.path.getsize(filepath) if os.path.exists(filepath) else 0
        headers = {"Range": f"bytes={existing_size}-"} if existing_size > 0 else {}
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
                            print(f"\r{percent:.2f}% | Left: {(total_size - downloaded) / (1024 * 1024):.2f} MB", end="")
                break
            except requests.exceptions.RequestException:
                print(f"\nConnection lost. Resuming...")
                time.sleep(3)
                existing_size = os.path.getsize(filepath)
                headers["Range"] = f"bytes={existing_size}-"
                downloaded = existing_size
        print()

    def _process_to_oci(self, local_path, filename):
        """Slices video and uploads to OCI."""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        remote_dir = f"stream_{ts}"
        chunks_dir = "chunks"
        os.makedirs(chunks_dir, exist_ok=True)

        print(f"Slicing: {filename}")
        cmd = ['ffmpeg', '-y', '-i', local_path, '-c', 'copy', '-sn', '-hls_time', '10', 
               '-hls_list_size', '0', '-f', 'hls', f"{chunks_dir}/index.m3u8"]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        if os.path.exists(local_path): os.remove(local_path)

        print("Uploading to OCI...")
        client = oci.object_storage.ObjectStorageClient(self.oci_config)
        for file in os.listdir(chunks_dir):
            path = os.path.join(chunks_dir, file)
            with open(path, 'rb') as f:
                client.put_object(self.namespace, self.bucket, f"{remote_dir}/{file}", f, 
                                 content_length=os.path.getsize(path))
            os.remove(path)
        os.rmdir(chunks_dir)
        print(f"✅ FINISHED: {remote_dir}/index.m3u8")

    def run_direct(self, url, filename="direct_video.mp4"):
        """Process a direct URL without Seedr."""
        print(f"--- Direct Mode Started ---")
        try:
            r = requests.head(url, allow_redirects=True)
            total_size = int(r.headers.get('content-length', 0))
        except: total_size = 0
            
        self.download_with_resume(url, filename, total_size)
        self._process_to_oci(filename, filename)

    def run_magnet(self, magnet):
        """Full Seedr to OCI pipeline."""
        token_obj = Token(access_token=self.seedr_token)
        seed = Seedr(token=token_obj)
        # CRITICAL: This prevents the AuthenticationError
        seed._refresh_access_token = lambda: None 

        # 1. CLEAN FIRST
        self.clear_seedr_storage(seed)
        
        # 2. ADD TORRENT
        print("Adding torrent...")
        try:
            seed.add_torrent(magnet)
        except Exception as e:
            return print(f"!! API Error: {e}")

        # 3. WAIT FOR FETCH
        print("Waiting for cloud fetch...")
        start_time = time.time()
        files = []
        while (time.time() - start_time) < 120:
            drive = seed.list_contents()
            if drive.files:
                files = drive.files
                break
            if drive.folders:
                files = seed.list_contents(drive.folders[0].id).files
                break
            time.sleep(10)

        if not files: return print("!! No files found (Fetch timeout).")

        # 4. DOWNLOAD AND PROCESS
        for file in files:
            fid = getattr(file, 'folder_file_id', getattr(file, 'id', None))
            if fid:
                details = seed.fetch_file(fid)
                safe_name = file.name.replace(" ", "_")
                print(f"Processing: {file.name}")
                self.download_with_resume(details.url, safe_name, int(file.size))
                self._process_to_oci(safe_name, safe_name)
        
        # 5. FINAL CLEAN
        self.clear_seedr_storage(seed)

if __name__ == "__main__":
    pipeline = MediaPipeline()
    # pipeline.run_magnet(os.getenv("magnet"))
    # pipeline.run_direct("https://rd24.seedr.cc/ff_get/5890607984/www.1TamilMV.rodeo%20-%20Peaky%20Blinders%20The%20Immortal%20Man%20(2026)%20HQ%20HDRip%20-%20720p%20-%20x264%20-%20[Tamil%20_%20Telugu%20_%20Hindi%20_%20Eng]%20-%20(DD_5.1%20-%20192Kbps).mkv?st=w9DvHUOAhz7wO4Vc4rrtLw&e=1774092185")