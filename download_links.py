import os
import time
import subprocess
import certifi

def main():
    # Read the links from the file
    with open('links.txt', 'r') as f:
        links = [line.strip() for line in f if line.strip()]

    # Ensure the media directory exists
    os.makedirs('media', exist_ok=True)

    # Read already successfully downloaded links to skip them
    downloaded_file = 'downloaded_links.txt'
    if os.path.exists(downloaded_file):
        with open(downloaded_file, 'r') as f:
            downloaded = set(line.strip() for line in f if line.strip())
    else:
        downloaded = set()

    success_count = 0
    failed_count = 0
    skipped_count = 0

    print(f"Total links: {len(links)}. Previously downloaded: {len(downloaded)}")

    for i, link in enumerate(links, start=1):
        if link in downloaded:
            skipped_count += 1
            continue

        print(f"\n--- Downloading video {i}/{len(links)} ---")
        print(f"Link: {link}")
        
        # Format filename as an enumeration: 001.mp4, 002.mp4, etc.
        output_template = f"media/{i:03d}.%(ext)s"
        
        # Call the yt-dlp executable we installed in the virtual environment
        cmd = [
            "venv/bin/yt-dlp",
            # Optionally extract only the best video format 
            "-f", "best",
            # Suppress yt-dlp warnings to keep the terminal output cleaner
            "--no-warnings",
            "-o", output_template,
            link
        ]
        
        # Set environment variables for SSL/TLS verification using certifi
        env = os.environ.copy()
        ca_bundle = certifi.where()
        env["SSL_CERT_FILE"] = ca_bundle
        env["REQUESTS_CA_BUNDLE"] = ca_bundle
        
        result = subprocess.run(cmd, env=env)
        
        if result.returncode == 0:
            success_count += 1
            print(f"✅ Successfully downloaded video {i}")
            # Record the link as successfully downloaded
            with open(downloaded_file, 'a') as f:
                f.write(link + '\n')
            downloaded.add(link)
        else:
            failed_count += 1
            print(f"❌ Failed to download video {i}")
            
        # Wait a few seconds between downloads to avoid getting rate-limited by platforms 
        # (Instagram, YouTube, etc.)
        # Only sleep if it's not the last item in the list
        if i < len(links):
            print("⏳ Waiting 5 seconds before the next download to avoid rate limits...")
            time.sleep(5)

    print(f"\n🎉 Finished! Successfully downloaded: {success_count}, Failed: {failed_count}, Skipped: {skipped_count}")

if __name__ == "__main__":
    main()
