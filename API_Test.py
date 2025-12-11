import requests
import base64
from PIL import Image
import io
import json

# Correct public Railway API URL
BASE_URL = "https://auto-visualizer-production.up.railway.app"

# Load your test JSON file
TEST_JSON_FILE = "Test_Data.json"

with open(TEST_JSON_FILE, "r") as f:
    cad_data = json.load(f)

# Example filter (optional)
filters = {
    "layers": ["A-WALL"]
}

# IMPORTANT: The key must be "data", not "json_data"
payload = {
    "data": cad_data,
    "filters": filters,
    "show_background": True
}

print("Sending request...")

response = requests.post(
    f"{BASE_URL}/render",
    json=payload
)

print("Status Code:", response.status_code)

# Display error details
if response.status_code != 200:
    print("Error response:")
    print(response.text)
    raise SystemExit

# Decode and display image
result = response.json()
image_base64 = result["image_base64"]

img_data = base64.b64decode(image_base64)
img = Image.open(io.BytesIO(img_data))
img.show()

print("Image displayed successfully!")
