import os
import json

INDEX_FILE = 'lottery/lottery_index.json'
MEDIA_DIR = 'lottery/lottery_media'

def main():
    if not os.path.exists(INDEX_FILE):
        print(f"Error: {INDEX_FILE} not found.")
        return

    with open(INDEX_FILE, 'r') as f:
        data = json.load(f)

    items = data.get('items', [])
    existing_srcs = {item.get('src') for item in items if item.get('src')}
    
    # Find the highest existing ID to continue incrementing
    next_id = max((item.get('id', 0) for item in items), default=0) + 1

    added_count = 0

    if not os.path.exists(MEDIA_DIR):
        print(f"Error: {MEDIA_DIR} not found.")
        return

    for filename in sorted(os.listdir(MEDIA_DIR)):
        # Skip hidden files
        if filename.startswith('.'):
            continue
            
        src = f"lottery_media/{filename}"
        
        if src not in existing_srcs:
            ext = os.path.splitext(filename)[1].lower()
            if ext in ['.mp4', '.mov', '.webm']:
                item_type = 'video'
            elif ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                item_type = 'image'
            else:
                item_type = 'unknown'

            new_item = {
                "id": next_id,
                "type": item_type,
                "src": src,
                "rarity": "common",
                "description": ""
            }
            
            items.append(new_item)
            next_id += 1
            added_count += 1
            print(f"Added new item: {filename}")

    if added_count > 0:
        with open(INDEX_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"\nSuccessfully added {added_count} new entries to {INDEX_FILE}.")
    else:
        print("No new media files found to add.")

if __name__ == "__main__":
    main()
