import os
import re
import sys
import json
import time
import shutil
import subprocess
import certifi

# === CONFIG ===
ICLOUD_DROPZONE = os.path.expanduser(
    "~/Library/Mobile Documents/com~apple~CloudDocs/lottery_dropzone"
)

# === PATHS (resolved from script location, so CWD doesn't matter) ===
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
REPO_MEDIA_DIR = os.path.join(REPO_ROOT, "lottery", "lottery_media")
INDEX_FILE = os.path.join(REPO_ROOT, "lottery", "lottery_index.json")
DOWNLOADED_LINKS = os.path.join(SCRIPT_DIR, "downloaded_links.txt")
FAILED_LINKS = os.path.join(SCRIPT_DIR, "failed_links.txt")
YT_DLP = os.path.join(SCRIPT_DIR, "venv", "bin", "yt-dlp")

DROP_LINKS_FILE = os.path.join(ICLOUD_DROPZONE, "links.txt")
DROP_MEDIA_DIR = os.path.join(ICLOUD_DROPZONE, "media")

MAKE_THUMBS_SCRIPT = os.path.join(SCRIPT_DIR, "make_thumbs.py")

VIDEO_EXTS = {".mp4", ".mov", ".webm"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


def next_number():
    nums = []
    for name in os.listdir(REPO_MEDIA_DIR):
        m = re.match(r"^(\d+)\.", name)
        if m:
            nums.append(int(m.group(1)))
    return max(nums, default=0) + 1


def infer_type(ext):
    ext = ext.lower()
    if ext in VIDEO_EXTS:
        return "video"
    if ext in IMAGE_EXTS:
        return "image"
    return "unknown"


def load_index():
    with open(INDEX_FILE, "r") as f:
        return json.load(f)


def save_index(data):
    with open(INDEX_FILE, "w") as f:
        json.dump(data, f, indent=2)


def append_index_entry(data, filename):
    items = data.setdefault("items", [])
    next_id = max((item.get("id", 0) for item in items), default=0) + 1
    ext = os.path.splitext(filename)[1]
    items.append({
        "id": next_id,
        "type": infer_type(ext),
        "src": f"lottery_media/{filename}",
        "rarity": "common",
        "description": "",
    })


def find_file_with_prefix(directory, prefix):
    for name in os.listdir(directory):
        if name.startswith(prefix):
            return name
    return None


def download_links_flow(counter, data):
    if not os.path.exists(DROP_LINKS_FILE):
        print(f"No links file at {DROP_LINKS_FILE}, skipping link downloads.\n")
        return counter

    with open(DROP_LINKS_FILE, "r") as f:
        links = [line.strip() for line in f if line.strip()]

    if os.path.exists(DOWNLOADED_LINKS):
        with open(DOWNLOADED_LINKS, "r") as f:
            downloaded = set(line.strip() for line in f if line.strip())
    else:
        downloaded = set()

    if os.path.exists(FAILED_LINKS):
        with open(FAILED_LINKS, "r") as f:
            failed_before = set(line.strip() for line in f if line.strip())
    else:
        failed_before = set()

    new_links = [l for l in links if l not in downloaded and l not in failed_before]
    print(f"=== LINKS ===")
    print(f"Total: {len(links)}. Downloaded: {len(downloaded)}. Previously failed: {len(failed_before)}. New: {len(new_links)}")

    if not new_links:
        return counter

    env = os.environ.copy()
    ca_bundle = certifi.where()
    env["SSL_CERT_FILE"] = ca_bundle
    env["REQUESTS_CA_BUNDLE"] = ca_bundle

    success_count = 0
    failed_count = 0

    for i, link in enumerate(new_links, start=1):
        print(f"\n--- Downloading {i}/{len(new_links)} as {counter:03d} ---")
        print(f"Link: {link}")

        output_template = os.path.join(REPO_MEDIA_DIR, f"{counter:03d}.%(ext)s")
        cmd = [
            YT_DLP,
            "-f", "best",
            "--no-warnings",
            "-o", output_template,
            link,
        ]
        result = subprocess.run(cmd, env=env)

        if result.returncode == 0:
            saved = find_file_with_prefix(REPO_MEDIA_DIR, f"{counter:03d}.")
            if saved is None:
                failed_count += 1
                print(f"❌ yt-dlp returned 0 but no file at {counter:03d}.*")
                with open(FAILED_LINKS, "a") as f:
                    f.write(link + "\n")
            else:
                success_count += 1
                print(f"✅ Saved as {saved}")
                append_index_entry(data, saved)
                with open(DOWNLOADED_LINKS, "a") as f:
                    f.write(link + "\n")
                counter += 1
        else:
            failed_count += 1
            print(f"❌ Failed to download {link}")
            with open(FAILED_LINKS, "a") as f:
                f.write(link + "\n")

        if i < len(new_links):
            print("⏳ Waiting 5 seconds before the next download...")
            time.sleep(5)

    print(f"\nLinks done. Success: {success_count}, Failed: {failed_count}")
    return counter


def drop_media_flow(counter, data):
    print(f"\n=== DROPS ===")
    if not os.path.isdir(DROP_MEDIA_DIR):
        print(f"No drop folder at {DROP_MEDIA_DIR}, skipping drops.")
        return counter

    drops = sorted(
        name for name in os.listdir(DROP_MEDIA_DIR)
        if not name.startswith(".") and os.path.isfile(os.path.join(DROP_MEDIA_DIR, name))
    )
    print(f"Files in dropzone: {len(drops)}")

    moved = 0
    for name in drops:
        src = os.path.join(DROP_MEDIA_DIR, name)
        ext = os.path.splitext(name)[1].lower()
        new_name = f"{counter:03d}{ext}"
        dest = os.path.join(REPO_MEDIA_DIR, new_name)
        print(f"Moving {name} → {new_name}")
        shutil.move(src, dest)
        append_index_entry(data, new_name)
        counter += 1
        moved += 1

    print(f"\nDrops moved: {moved}")
    return counter


def main():
    os.makedirs(REPO_MEDIA_DIR, exist_ok=True)
    data = load_index()
    counter = next_number()
    print(f"Starting numbering at #{counter:03d}\n")

    counter = download_links_flow(counter, data)
    counter = drop_media_flow(counter, data)

    save_index(data)

    print("\n=== THUMBS ===")
    result = subprocess.run([sys.executable, MAKE_THUMBS_SCRIPT])
    if result.returncode != 0:
        print("⚠️  thumb generation reported errors (see above); continuing anyway")

    print("\n🎉 Done. Review `git status` and `git diff lottery/lottery_index.json`, then commit & push.")


if __name__ == "__main__":
    main()
