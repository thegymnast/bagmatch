import os
import random
import re
from datetime import datetime

from PIL import Image, ImageDraw

import db
from vision import colour_name, rgb_to_lab


PALETTE = [
    ("charcoal", (55, 58, 63)),
    ("silver", (170, 174, 178)),
    ("navy", (31, 55, 103)),
    ("teal", (30, 122, 128)),
    ("burgundy", (112, 34, 57)),
    ("olive", (105, 111, 58)),
    ("red", (185, 48, 47)),
    ("blue", (47, 99, 164)),
    ("tan", (181, 139, 90)),
    ("cream", (223, 211, 183)),
    ("purple", (105, 70, 135)),
    ("orange", (214, 116, 48)),
    ("forest green", (43, 91, 61)),
    ("white", (225, 225, 219)),
    ("black", (37, 39, 43)),
]
FLIGHTS = ["CV104", "CV218", "CV407", "CV512", "CV633", "CV880"]
NAMES = [
    "Avery Morgan", "Jordan Lee", "Sam Taylor", "Riley Chen",
    "Casey Patel", "Alex Rivera", "Jamie Brooks", "Drew Wilson",
]
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PHOTO_DIR = os.path.join(BASE_DIR, "data", "luggage_photos")


def _manual_photo_path(tag_id):
    filename = re.sub(r"[^A-Za-z0-9._-]", "_", tag_id)
    for extension in (".jpg", ".jpeg", ".png"):
        path = os.path.join(PHOTO_DIR, filename + extension)
        if os.path.isfile(path):
            return path
    return None


def sync_bag_photos():
    if not os.path.isdir(PHOTO_DIR):
        os.makedirs(PHOTO_DIR, exist_ok=True)
    updated = 0
    thumbs_dir = os.path.join(BASE_DIR, "data", "thumbs")
    with db.get_connection() as connection:
        bags = connection.execute(
            "SELECT tag_id, thumb_path, r, g, b, length_cm, width_cm FROM bags"
        ).fetchall()
        for bag in bags:
            path = _manual_photo_path(bag["tag_id"])
            if path is None and bag["thumb_path"] and os.path.isfile(bag["thumb_path"]):
                continue
            if path is None and re.fullmatch(r"BAG-\d{4}", bag["tag_id"]):
                os.makedirs(thumbs_dir, exist_ok=True)
                path = os.path.join(thumbs_dir, bag["tag_id"].lower() + ".jpg")
                _thumbnail(
                    path,
                    (bag["r"], bag["g"], bag["b"]),
                    bag["length_cm"],
                    bag["width_cm"],
                )
            if path and path != bag["thumb_path"]:
                connection.execute(
                    "UPDATE bags SET thumb_path = ? WHERE tag_id = ?",
                    (path, bag["tag_id"]),
                )
                updated += 1
    return updated


def _thumbnail(path, rgb, length, width):
    image = Image.new("RGB", (360, 240), (239, 241, 244))
    draw = ImageDraw.Draw(image)
    bag_width = int(145 + width * 0.65)
    bag_height = int(115 + length * 0.45)
    left = (360 - bag_width) // 2
    top = (240 - bag_height) // 2 + 10
    draw.rounded_rectangle(
        (left, top, left + bag_width, top + bag_height),
        radius=18,
        fill=tuple(rgb),
        outline=(65, 65, 65),
        width=3,
    )
    draw.rounded_rectangle(
        (left + 38, top - 15, left + bag_width - 38, top + 8),
        radius=10,
        outline=(65, 65, 65),
        width=4,
    )
    draw.line(
        (left + 18, top + bag_height // 2, left + bag_width - 18, top + bag_height // 2),
        fill=tuple(max(0, min(255, channel - 25)) for channel in rgb),
        width=3,
    )
    image.save(path, quality=88)


def seed_data(count=40, force=False):
    if count < 10:
        raise ValueError("Generate at least 10 bags for useful matching")
    db.init_db()
    if db.get_count("bags") and not force:
        sync_bag_photos()
        return 0
    if force:
        db.purge_all()

    random.seed(731)
    thumbs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "thumbs")
    os.makedirs(thumbs_dir, exist_ok=True)
    generated = []
    for index in range(count):
        if index in (0, 1):
            palette_name, base = "silver", (162, 166, 170)
        elif index in (2, 3):
            palette_name, base = "charcoal", (58, 61, 65)
        else:
            palette_name, base = random.choice(PALETTE)
        if index in (1, 3):
            colour = base
            weight = 18.9 if index == 1 else 24.7
            length, width, height = (67, 43, 26) if index == 1 else (68, 44, 27)
        else:
            colour = tuple(max(0, min(255, channel + random.randint(-12, 12))) for channel in base)
            weight = round(random.uniform(8.5, 30.0), 1)
            length = round(random.uniform(50, 78), 1)
            width = round(random.uniform(33, 51), 1)
            height = round(random.uniform(18, 33), 1)
        lab = rgb_to_lab(colour)
        tag_id = "BAG-{:04d}".format(index + 1)
        path = _manual_photo_path(tag_id)
        if path is None:
            path = os.path.join(thumbs_dir, "{}.jpg".format(tag_id.lower()))
            _thumbnail(path, colour, length, width)
        bag = {
            "tag_id": tag_id,
            "flight": random.choice(FLIGHTS),
            "checkin_time": datetime.now().isoformat(timespec="seconds"),
            "weight_kg": weight,
            "length_cm": length,
            "width_cm": width,
            "height_cm": height,
            "r": colour[0],
            "g": colour[1],
            "b": colour[2],
            "L": lab[0],
            "a": lab[1],
            "b_lab": lab[2],
            "colour_name": palette_name if index < 4 else colour_name(colour),
            "thumb_path": path,
            "status": "checked_in",
        }
        passenger = {
            "name": NAMES[index % len(NAMES)],
            "phone": "+1555{:07d}".format(1000000 + index),
            "email": "traveler{}@example.test".format(index + 1),
        }
        db.insert_bag(bag, passenger)
        generated.append(bag)

    report_count = min(len(generated), max(10, int(len(generated) * 0.6)))
    for index, bag in enumerate(generated[:report_count]):
        report_id = "SYN-{:04d}".format(index + 1)
        rgb = [bag["r"], bag["g"], bag["b"]]
        noisy = tuple(max(0, min(255, value + random.randint(-7, 7))) for value in rgb)
        lab = rgb_to_lab(noisy)
        report = {
            "report_id": report_id,
            "reported_time": datetime.now().isoformat(timespec="seconds"),
            "passenger_name": NAMES[index % len(NAMES)],
            "weight_kg": round(bag["weight_kg"] + random.uniform(-0.7, 0.7), 1),
            "length_cm": round(bag["length_cm"] + random.uniform(-3.0, 3.0), 1),
            "width_cm": round(bag["width_cm"] + random.uniform(-2.0, 2.0), 1),
            "height_cm": round(bag["height_cm"] + random.uniform(-1.5, 1.5), 1),
            "r": noisy[0],
            "g": noisy[1],
            "b": noisy[2],
            "L": lab[0],
            "a": lab[1],
            "b_lab": lab[2],
            "colour_name": colour_name(noisy),
            "flight": bag["flight"],
        }
        db.insert_lost_report(report)
        with db.get_connection() as connection:
            connection.execute(
                "INSERT INTO synthetic_truth (report_id, tag_id) VALUES (?, ?)",
                (report_id, bag["tag_id"]),
            )
    db.log_event("seeded", "synthetic-data", "system", "Generated {} bags".format(count))
    sync_bag_photos()
    return count


if __name__ == "__main__":
    print("Generated {} synthetic bags.".format(seed_data()))
