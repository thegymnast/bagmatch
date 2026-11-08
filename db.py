import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("BAG_TRACKER_DB", os.path.join(BASE_DIR, "bags.db"))


@contextmanager
def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_db():
    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS bags (
                tag_id TEXT PRIMARY KEY,
                flight TEXT,
                checkin_time TEXT NOT NULL,
                weight_kg REAL NOT NULL,
                length_cm REAL NOT NULL,
                width_cm REAL NOT NULL,
                height_cm REAL NOT NULL,
                r INTEGER NOT NULL,
                g INTEGER NOT NULL,
                b INTEGER NOT NULL,
                L REAL NOT NULL,
                a REAL NOT NULL,
                b_lab REAL NOT NULL,
                colour_name TEXT NOT NULL,
                thumb_path TEXT,
                status TEXT NOT NULL DEFAULT 'checked_in'
            );
            CREATE TABLE IF NOT EXISTS passengers (
                tag_id TEXT PRIMARY KEY REFERENCES bags(tag_id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                phone TEXT,
                email TEXT
            );
            CREATE TABLE IF NOT EXISTS untagged (
                found_id TEXT PRIMARY KEY,
                found_time TEXT NOT NULL,
                weight_kg REAL NOT NULL,
                length_cm REAL NOT NULL,
                width_cm REAL NOT NULL,
                height_cm REAL NOT NULL,
                r INTEGER NOT NULL,
                g INTEGER NOT NULL,
                b INTEGER NOT NULL,
                L REAL NOT NULL,
                a REAL NOT NULL,
                b_lab REAL NOT NULL,
                colour_name TEXT NOT NULL,
                thumb_path TEXT,
                status TEXT NOT NULL DEFAULT 'found',
                matched_tag_id TEXT REFERENCES bags(tag_id)
            );
            CREATE TABLE IF NOT EXISTS lost_reports (
                report_id TEXT PRIMARY KEY,
                reported_time TEXT NOT NULL,
                passenger_name TEXT,
                weight_kg REAL NOT NULL,
                length_cm REAL NOT NULL,
                width_cm REAL NOT NULL,
                height_cm REAL NOT NULL,
                r INTEGER NOT NULL,
                g INTEGER NOT NULL,
                b INTEGER NOT NULL,
                L REAL NOT NULL,
                a REAL NOT NULL,
                b_lab REAL NOT NULL,
                colour_name TEXT NOT NULL,
                flight TEXT
            );
            CREATE TABLE IF NOT EXISTS events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                type TEXT NOT NULL,
                id TEXT NOT NULL,
                actor TEXT NOT NULL,
                details TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS synthetic_truth (
                report_id TEXT PRIMARY KEY REFERENCES lost_reports(report_id) ON DELETE CASCADE,
                tag_id TEXT NOT NULL REFERENCES bags(tag_id) ON DELETE CASCADE
            );
            """
        )


def insert_bag(bag, passenger=None):
    fields = (
        "tag_id", "flight", "checkin_time", "weight_kg", "length_cm",
        "width_cm", "height_cm", "r", "g", "b", "L", "a", "b_lab",
        "colour_name", "thumb_path", "status",
    )
    with get_connection() as connection:
        connection.execute(
            "INSERT INTO bags ({}) VALUES ({})".format(
                ", ".join(fields), ", ".join("?" for _ in fields)
            ),
            tuple(bag.get(field) for field in fields),
        )
        if passenger:
            connection.execute(
                "INSERT INTO passengers (tag_id, name, phone, email) VALUES (?, ?, ?, ?)",
                (
                    bag["tag_id"],
                    passenger.get("name", ""),
                    passenger.get("phone"),
                    passenger.get("email"),
                ),
            )


def get_all_bags():
    with get_connection() as connection:
        return connection.execute(
            "SELECT * FROM bags ORDER BY checkin_time DESC"
        ).fetchall()


def get_all_passengers():
    with get_connection() as connection:
        return connection.execute(
            "SELECT tag_id, name, phone, email FROM passengers ORDER BY tag_id"
        ).fetchall()


def log_event(event_type, entity_id, actor, details):
    with get_connection() as connection:
        connection.execute(
            "INSERT INTO events (timestamp, type, id, actor, details) VALUES (?, ?, ?, ?, ?)",
            (
                datetime.now().isoformat(timespec="seconds"),
                event_type,
                str(entity_id),
                actor,
                details,
            ),
        )


def insert_untagged(item):
    fields = (
        "found_id", "found_time", "weight_kg", "length_cm", "width_cm",
        "height_cm", "r", "g", "b", "L", "a", "b_lab", "colour_name",
        "thumb_path", "status", "matched_tag_id",
    )
    with get_connection() as connection:
        connection.execute(
            "INSERT INTO untagged ({}) VALUES ({})".format(
                ", ".join(fields), ", ".join("?" for _ in fields)
            ),
            tuple(item.get(field) for field in fields),
        )


def insert_lost_report(report):
    fields = (
        "report_id", "reported_time", "passenger_name", "weight_kg",
        "length_cm", "width_cm", "height_cm", "r", "g", "b", "L", "a",
        "b_lab", "colour_name", "flight",
    )
    with get_connection() as connection:
        connection.execute(
            "INSERT INTO lost_reports ({}) VALUES ({})".format(
                ", ".join(fields), ", ".join("?" for _ in fields)
            ),
            tuple(report.get(field) for field in fields),
        )


def get_bag(tag_id):
    with get_connection() as connection:
        return connection.execute(
            "SELECT * FROM bags WHERE tag_id = ?", (tag_id,)
        ).fetchone()


def get_passenger(tag_id):
    with get_connection() as connection:
        return connection.execute(
            "SELECT * FROM passengers WHERE tag_id = ?", (tag_id,)
        ).fetchone()


def get_untagged(found_id):
    with get_connection() as connection:
        return connection.execute(
            "SELECT * FROM untagged WHERE found_id = ?", (found_id,)
        ).fetchone()


def get_lost_reports():
    with get_connection() as connection:
        return connection.execute(
            "SELECT * FROM lost_reports ORDER BY reported_time DESC"
        ).fetchall()


def get_all_untagged():
    with get_connection() as connection:
        return connection.execute(
            "SELECT * FROM untagged ORDER BY found_time DESC"
        ).fetchall()


def confirm_match(found_id, tag_id):
    with get_connection() as connection:
        connection.execute(
            "UPDATE untagged SET status = 'retagged', matched_tag_id = ? WHERE found_id = ?",
            (tag_id, found_id),
        )
        connection.execute(
            "UPDATE bags SET status = 'matched' WHERE tag_id = ?", (tag_id,)
        )


def get_events(limit=500):
    with get_connection() as connection:
        return connection.execute(
            "SELECT timestamp, type, id, actor, details FROM events "
            "ORDER BY event_id DESC LIMIT ?",
            (limit,),
        ).fetchall()


def get_synthetic_truth():
    with get_connection() as connection:
        return connection.execute(
            "SELECT report_id, tag_id FROM synthetic_truth"
        ).fetchall()


def get_count(table):
    allowed = {"bags", "untagged", "lost_reports"}
    if table not in allowed:
        raise ValueError("Unsupported table")
    with get_connection() as connection:
        return connection.execute(
            "SELECT COUNT(*) AS count FROM {}".format(table)
        ).fetchone()["count"]


def purge_all():
    with get_connection() as connection:
        connection.executescript(
            """
            DELETE FROM synthetic_truth;
            DELETE FROM passengers;
            DELETE FROM lost_reports;
            DELETE FROM untagged;
            DELETE FROM bags;
            DELETE FROM events;
            """
        )
