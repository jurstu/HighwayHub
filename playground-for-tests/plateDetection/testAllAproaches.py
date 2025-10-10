import os
import cv2
import requests
import hashlib
from urllib.parse import urlparse



def get_image_from_url(url: str) -> str:
    """Download image from URL if not already cached, then return local file path."""
    os.makedirs("assets", exist_ok=True)

    # Derive file extension from URL if present
    parsed = urlparse(url)
    _, ext = os.path.splitext(parsed.path)
    ext = ext if ext else ".jpg"  # default if missing

    # Hash the URL to create a unique filename
    url_hash = hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]
    filename = f"{url_hash}{ext}"
    filepath = os.path.join("assets", filename)

    # Use cached version if available
    if os.path.exists(filepath):
        print(f"✅ Using cached image: {filepath}")
        return filepath

    # Otherwise, download it
    print(f"⬇️ Downloading image from {url}")
    response = requests.get(url, timeout=10)
    response.raise_for_status()

    with open(filepath, "wb") as f:
        f.write(response.content)

    print(f"💾 Saved image to {filepath}")
    return filepath







def find_n_detect(image):
    














if __name__ == "__main__":
    url = "https://tablica-rejestracyjna.pl/images/photos/20251009180009.jpeg"

    local_path = get_image_from_url(url)

    # Load with OpenCV
    img = cv2.imread(local_path)
    if img is None:
        raise ValueError(f"Failed to load image: {local_path}")

    cv2.imshow("Image", img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()




