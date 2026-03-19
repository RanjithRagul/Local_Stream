import os
import subprocess
import requests
import oci
from datetime import datetime
from dotenv import load_dotenv

# Load secrets from .env file
load_dotenv()

# Configuration
USER_OCID = os.getenv("OCI_USER_OCID")
TENANCY_OCID = os.getenv("OCI_TENANCY_OCID")
FINGERPRINT = os.getenv("OCI_FINGERPRINT")
PRIVATE_KEY = os.getenv("OCI_PRIVATE_KEY")
REGION = os.getenv("OCI_REGION", "us-ashburn-1")
NAMESPACE = os.getenv("OCI_NAMESPACE")
BUCKET = os.getenv("OCI_BUCKET_NAME")

# Secret URL from .env
URL = os.getenv("DIRECT_DOWNLOAD_URL")

# Timing and Paths
TS = datetime.now().strftime("%Y%m%d_%H%M%S")
TEMP_VIDEO = f"src_{TS}.mp4"
REMOTE_DIR = f"stream_{TS}"
LOCAL_DIR = "chunks"

OCI_CONFIG = {
    "user": USER_OCID,
    "key_content": PRIVATE_KEY,
    "fingerprint": FINGERPRINT,
    "tenancy": TENANCY_OCID,
    "region": REGION
}

class ProgressStream:
    def __init__(self, file_obj, size, name):
        self.file_obj, self.size, self.name, self.read_bytes = file_obj, size, name, 0
    def read(self, n):
        data = self.file_obj.read(n)
        if data:
            self.read_bytes += len(data)
            print(f"Uploading {self.name}: {int(self.read_bytes/self.size*100)}%", end="\r")
        return data

def main():
    if not URL: return print("!! URL not found in .env file.")

    print(f"1. Downloading from secret URL...")
    with requests.get(URL, stream=True) as r:
        r.raise_for_status()
        with open(TEMP_VIDEO, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024*1024): f.write(chunk)

    print("\n2. Slicing into HLS...")
    os.makedirs(LOCAL_DIR, exist_ok=True)
    cmd = ['ffmpeg', '-y', '-i', TEMP_VIDEO, '-c', 'copy', '-sn', '-hls_time', '10', 
           '-hls_list_size', '0', '-f', 'hls', f"{LOCAL_DIR}/index.m3u8"]
    
    if subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode != 0:
        return print("!! FFmpeg failed.")
    os.remove(TEMP_VIDEO)

    print("3. Uploading to OCI...")
    client = oci.object_storage.ObjectStorageClient(OCI_CONFIG)
    for file in os.listdir(LOCAL_DIR):
        path = os.path.join(LOCAL_DIR, file)
        size = os.path.getsize(path)
        with open(path, 'rb') as f:
            client.put_object(NAMESPACE, BUCKET, f"{REMOTE_DIR}/{file}", 
                             ProgressStream(f, size, file), content_length=size)
        os.remove(path)
    
    os.rmdir(LOCAL_DIR)
    print(f"\nFINISHED: {BUCKET}/{REMOTE_DIR}/index.m3u8")

if __name__ == "__main__":
    main()