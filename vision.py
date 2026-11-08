import io
import os

import cv2
import numpy as np
from PIL import Image
from skimage.color import rgb2lab


def image_to_rgb(image):
    if isinstance(image, bytes):
        image = Image.open(io.BytesIO(image))
    if isinstance(image, Image.Image):
        return np.asarray(image.convert("RGB"))
    if isinstance(image, np.ndarray):
        if image.ndim == 2:
            return cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        if image.shape[2] == 4:
            return cv2.cvtColor(image, cv2.COLOR_RGBA2RGB)
        return image[:, :, :3].copy()
    raise TypeError("Image must be bytes, a PIL image, or a NumPy array")


def analyze_bag(image, reference=None):
    rgb = image_to_rgb(image)
    if reference is None:
        gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        mask = cv2.threshold(gray, 35, 255, cv2.THRESH_BINARY)[1]
    else:
        reference_rgb = image_to_rgb(reference)
        if reference_rgb.shape[:2] != rgb.shape[:2]:
            reference_rgb = cv2.resize(
                reference_rgb, (rgb.shape[1], rgb.shape[0])
            )
        difference = cv2.absdiff(rgb, reference_rgb)
        gray = cv2.cvtColor(difference, cv2.COLOR_RGB2GRAY)
        mask = cv2.threshold(gray, 24, 255, cv2.THRESH_BINARY)[1]

    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    contours, _ = cv2.findContours(
        mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    contours = [contour for contour in contours if cv2.contourArea(contour) > 100]
    if not contours:
        raise ValueError(
            "No bag outline was detected. Use a contrasting background or adjust the lighting."
        )

    contour = max(contours, key=cv2.contourArea)
    x, y, width, height = cv2.boundingRect(contour)
    object_mask = np.zeros(mask.shape, dtype=np.uint8)
    cv2.drawContours(object_mask, [contour], -1, 255, thickness=-1)
    pixels = rgb[object_mask > 0]
    median_rgb = np.median(pixels, axis=0).astype(int)
    lab = rgb2lab((median_rgb.astype(np.float32) / 255.0).reshape(1, 1, 3))[0, 0]
    overlay = rgb.copy()
    cv2.drawContours(overlay, [contour], -1, (0, 255, 0), 3)

    result = {
        "rgb": tuple(int(value) for value in median_rgb),
        "lab": tuple(float(value) for value in lab),
        "outline": Image.fromarray(overlay),
    }
    return result


def save_image(image, path):
    rgb = image_to_rgb(image)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    Image.fromarray(rgb).save(path, format="JPEG", quality=88)


def rgb_to_lab(rgb):
    values = np.asarray(rgb, dtype=np.float32).reshape(1, 1, 3) / 255.0
    return tuple(float(value) for value in rgb2lab(values)[0, 0])


def colour_name(rgb):
    r, g, b = [int(value) for value in rgb]
    maximum, minimum = max(r, g, b), min(r, g, b)
    if maximum - minimum < 28:
        if maximum < 55:
            return "black"
        if minimum > 205:
            return "white"
        if maximum < 125:
            return "dark grey"
        if maximum > 185:
            return "light grey"
        return "grey"
    if r >= g and r >= b:
        return "orange" if g > r * 0.55 else "red"
    if g >= r and g >= b:
        return "yellow" if r > g * 0.65 else "green"
    return "purple" if r > g * 1.25 else "blue"
