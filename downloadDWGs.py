import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BASE_PAGE = "https://afd.calpoly.edu/facilities/campus-maps/building-floor-plans/autocad/"
BASE_URL = "https://afd.calpoly.edu"
OUTPUT_DIR = "DWGs"

os.makedirs(OUTPUT_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

print("Fetching page...")
response = requests.get(BASE_PAGE, headers=HEADERS, timeout=30)
response.raise_for_status()

soup = BeautifulSoup(response.text, "html.parser")

# Collect DWG links
dwg_links = []
for a in soup.find_all("a", href=True):
    href = a["href"]
    if href.lower().endswith(".dwg"):
        dwg_links.append(urljoin(BASE_URL, href))

print(f"Found {len(dwg_links)} DWG files")

failed = []

for i, url in enumerate(dwg_links, start=1):
    filename = os.path.basename(url)
    output_path = os.path.join(OUTPUT_DIR, filename)

    # Skip already downloaded files
    if os.path.exists(output_path):
        print(f"[{i}/{len(dwg_links)}] Skipping existing: {filename}")
        continue

    print(f"[{i}/{len(dwg_links)}] Downloading {filename}...")

    try:
        with requests.get(url, headers=HEADERS, stream=True, timeout=60) as r:
            if r.status_code != 200:
                print(f"  ⚠️  Failed ({r.status_code})")
                failed.append((filename, r.status_code))
                continue

            with open(output_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

    except requests.exceptions.RequestException as e:
        print(f"  ❌ Error: {e}")
        failed.append((filename, str(e)))

# Write failures to a log file
if failed:
    with open("failed_downloads.txt", "w") as f:
        for name, error in failed:
            f.write(f"{name} -> {error}\n")

    print(f"\nCompleted with {len(failed)} failures.")
    print("See failed_downloads.txt for details.")
else:
    print("\nAll files downloaded successfully!")
