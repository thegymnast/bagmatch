import os
import re
import uuid
from datetime import datetime

import pandas as pd
import qrcode
import streamlit as st
from PIL import Image

import db
import theme
from matcher import rank_bags
from seed import seed_data, sync_bag_photos
from vision import (
    analyze_bag,
    colour_name,
    rgb_to_lab,
    save_image,
)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGE_DIR = os.path.join(BASE_DIR, "data", "images")
QR_DIR = os.path.join(BASE_DIR, "data", "qr")


def _saved_bag_photo_path(tag_id):
    filename = re.sub(r"[^A-Za-z0-9._-]", "_", tag_id)
    for extension in (".jpg", ".jpeg", ".png"):
        path = os.path.join(BASE_DIR, "data", "luggage_photos", filename + extension)
        if os.path.isfile(path):
            return path
    return None


def _image_bytes(upload):
    return upload.getvalue() if upload is not None else None


def _color_measurement(rgb):
    lab = rgb_to_lab(rgb)
    return {
        "r": int(rgb[0]),
        "g": int(rgb[1]),
        "b": int(rgb[2]),
        "L": lab[0],
        "a": lab[1],
        "b_lab": lab[2],
        "colour_name": colour_name(rgb),
    }


def _show_ranked(results):
    if not results:
        st.info("No bags passed the loose weight and size filters.")
        return
    for rank, result in enumerate(results, start=1):
        bag = result["bag"]
        columns = st.columns([1, 3])
        with columns[0]:
            if bag["thumb_path"] and os.path.exists(bag["thumb_path"]):
                st.image(bag["thumb_path"], use_column_width=True)
            else:
                st.markdown(
                    '<div style="background:rgb({},{},{});height:90px;border-radius:8px"></div>'.format(
                        bag["r"], bag["g"], bag["b"]
                    ),
                    unsafe_allow_html=True,
                )
        with columns[1]:
            st.markdown(
                "**#{} {}** · {} · {:.1f} kg · {:.0f} × {:.0f} × {:.0f} cm".format(
                    rank,
                    bag["tag_id"],
                    bag["colour_name"],
                    bag["weight_kg"],
                    bag["length_cm"],
                    bag["width_cm"],
                    bag["height_cm"],
                )
            )
            st.caption(" · ".join(result["reasons"]))
            st.progress(max(0.0, min(1.0, 1.0 - result["score"])))


def _capture_image(label, key):
    camera = st.camera_input(label, key="camera_" + key)
    if camera is not None:
        return _image_bytes(camera)
    upload = st.file_uploader(
        "Or upload a photo", type=["jpg", "jpeg", "png"], key="upload_" + key
    )
    return _image_bytes(upload)


def _reference_controls():
    st.subheader("Photo setup")
    reference_camera = st.camera_input(
        "Photograph the empty black box", key="reference_camera"
    )
    reference_upload = st.file_uploader(
        "Or upload the empty-box reference photo",
        type=["jpg", "jpeg", "png"],
        key="reference_photo",
    )
    reference = reference_camera or reference_upload
    if reference is not None:
        st.session_state["reference_rgb"] = Image.open(reference).convert("RGB")
        st.success("Reference photo loaded for this session.")
    if st.session_state.get("reference_rgb") is not None:
        st.image(st.session_state["reference_rgb"], caption="Current empty-box reference")
    st.caption("Use the same camera position and lighting for the reference and all bag photos.")


def home_page():
    st.title("MatchABag")
    st.write("A small concept app for recording, matching and safely re-tagging checked bags.")
    columns = st.columns(3)
    columns[0].metric("Checked-in bags", db.get_count("bags"))
    columns[1].metric("Untagged found", db.get_count("untagged"))
    columns[2].metric("Lost reports", db.get_count("lost_reports"))
    st.markdown(
        """
        **How it works?**
        1. Check in a tagged bag and record its measurements and owner.
        2. Search a lost-bag report or photograph an untagged found bag.
        3. Staff can confirm a candidate before a mock SMS is recorded.

        **Limits:** Weight and dimensions are typed in. Lighting is controlled in this concept,
        so photograph all demo bags under the same conditions. Synthetic data demonstrates
        the matching logic, not real-world accuracy.
        """
    )
    if st.button("Load synthetic demo data"):
        added = seed_data()
        st.success("Loaded {} synthetic bags.".format(added) if added else "Synthetic data is already loaded.")
        st.experimental_rerun()


def checkin_page():
    st.title("Check in a bag")
    _reference_controls()
    with st.form("checkin_form"):
        tag_id = st.text_input("Bag tag ID")
        flight = st.text_input("Flight")
        owner_name = st.text_input("Passenger name")
        phone = st.text_input("Phone (used only after staff confirms a match)")
        email = st.text_input("Email")
        weight = st.number_input("Weight (kg)", min_value=0.1, value=18.0, step=0.1)
        length = st.number_input("Length (cm)", min_value=1.0, value=67.0)
        width = st.number_input("Width (cm)", min_value=1.0, value=43.0)
        height = st.number_input("Height (cm)", min_value=1.0, value=25.0, step=0.5)
        photo = _capture_image("Photograph the bag in the box", "checkin")
        submitted = st.form_submit_button("Save check-in")
    if photo:
        if st.session_state.get("reference_rgb") is None:
            st.error("Photograph the empty box reference before analyzing a bag.")
            result = None
        else:
            try:
                result = analyze_bag(
                    photo,
                    st.session_state["reference_rgb"],
                )
                st.image(result["outline"], caption="Detected bag outline")
                st.markdown(
                    "Median colour: **{}** · RGB {}".format(
                        colour_name(result["rgb"]), result["rgb"]
                    )
                )
                st.color_picker(
                    "Detected colour", value="#{:02x}{:02x}{:02x}".format(*result["rgb"]),
                    disabled=True,
                )
            except ValueError as error:
                st.error(str(error))
                result = None
    else:
        result = None
    if submitted:
        if not tag_id.strip() or not owner_name.strip():
            st.error("Enter both a tag ID and passenger name.")
        elif not photo or result is None:
            st.error("Provide a usable photo before saving.")
        else:
            tag = tag_id.strip()
            if db.get_bag(tag) is not None:
                st.error("That tag ID is already checked in.")
                return
            image_path = _saved_bag_photo_path(tag)
            if image_path is None:
                image_path = os.path.join(IMAGE_DIR, "{}.jpg".format(uuid.uuid4().hex))
            save_image(photo, image_path)
            rgb, lab = result["rgb"], result["lab"]
            bag = {
                "tag_id": tag,
                "flight": flight.strip() or None,
                "checkin_time": datetime.now().isoformat(timespec="seconds"),
                "weight_kg": weight,
                "length_cm": length,
                "width_cm": width,
                "height_cm": height,
                "r": rgb[0], "g": rgb[1], "b": rgb[2],
                "L": lab[0], "a": lab[1], "b_lab": lab[2],
                "colour_name": colour_name(rgb),
                "thumb_path": image_path,
                "status": "checked_in",
            }
            db.insert_bag(
                bag,
                {"name": owner_name.strip(), "phone": phone.strip(), "email": email.strip()},
            )
            db.log_event("checkin", tag, owner_name.strip(), "Bag checked in")
            st.image(image_path, caption="Saved check-in photo", width=320)
            st.success("Bag {} checked in.".format(tag))


def find_bag_page():
    st.title("Find my bag")
    colour_source = st.radio(
        "How would you like to provide the bag colour?",
        ["Choose a colour", "Use a photo"],
        horizontal=True,
    )
    if colour_source == "Use a photo":
        _reference_controls()
    with st.form("lost_search"):
        weight = st.number_input("Approximate weight (kg)", min_value=0.1, value=18.0, step=0.5)
        length = st.number_input("Approximate length (cm)", min_value=1.0, value=67.0)
        width = st.number_input("Approximate width (cm)", min_value=1.0, value=43.0)
        height = st.number_input("Approximate height (cm)", min_value=1.0, value=25.0)
        flight = st.text_input("Flight (optional)")
        if colour_source == "Choose a colour":
            selected_colour = st.color_picker("Approximate bag colour", "#6a7078")
            photo = None
        else:
            selected_colour = None
            photo = _capture_image("Photograph the bag to detect its colour", "lost")
        search = st.form_submit_button("Rank likely bags")
    if search:
        if colour_source == "Choose a colour":
            rgb = tuple(
                int(selected_colour[index:index + 2], 16)
                for index in (1, 3, 5)
            )
            colour_result = {"rgb": rgb}
        else:
            if not photo:
                st.error("Photograph or upload the bag so its colour can be detected.")
                colour_result = None
            elif st.session_state.get("reference_rgb") is None:
                st.error("Photograph the empty box reference before analyzing a bag.")
                colour_result = None
            else:
                try:
                    colour_result = analyze_bag(photo, st.session_state["reference_rgb"])
                except ValueError as error:
                    st.error(str(error))
                    colour_result = None
        if colour_result is not None:
            if "outline" in colour_result:
                st.image(colour_result["outline"], caption="Detected bag outline")
            query = {
                "weight_kg": weight,
                "length_cm": length,
                "width_cm": width,
                "height_cm": height,
            }
            query.update(_color_measurement(colour_result["rgb"]))
            results = rank_bags(query, db.get_all_bags(), flight=flight.strip() or None)
            report_id = "RPT-" + uuid.uuid4().hex[:8].upper()
            db.insert_lost_report(
                {
                    "report_id": report_id,
                    "reported_time": datetime.now().isoformat(timespec="seconds"),
                    "passenger_name": None,
                    "weight_kg": weight,
                    "length_cm": length,
                    "width_cm": width,
                    "height_cm": height,
                    "r": query["r"],
                    "g": query["g"],
                    "b": query["b"],
                    "L": query["L"],
                    "a": query["a"],
                    "b_lab": query["b_lab"],
                    "colour_name": query["colour_name"],
                    "flight": flight.strip() or None,
                }
            )
            db.log_event("lost_report", report_id, "passenger", "Lost bag search submitted")
            st.session_state["active_lost_report_id"] = report_id
            st.session_state["active_lost_candidates"] = [
                {
                    "bag": dict(item["bag"]),
                    "score": item["score"],
                    "reasons": item["reasons"],
                }
                for item in results
            ]
    report_id = st.session_state.get("active_lost_report_id")
    candidates = st.session_state.get("active_lost_candidates", [])
    if report_id:
        _show_ranked(candidates)
        if candidates:
            st.subheader("Confirm a result")
            options = [
                "{} — {}".format(item["bag"]["tag_id"], item["bag"]["colour_name"])
                for item in candidates
            ]
            selected = st.selectbox("Staff-confirmed bag", options, key="lost_confirm")
            if st.button("Confirm match and send mock SMS", key="lost_sms"):
                tag_id = selected.split(" — ", 1)[0]
                _send_mock_sms(tag_id, report_id)
                st.session_state.pop("active_lost_report_id", None)
                st.session_state.pop("active_lost_candidates", None)


def _send_mock_sms(tag_id, source_id):
    owner = db.get_passenger(tag_id)
    if owner is None:
        st.error("No passenger contact is associated with this bag.")
        return
    message = "Mock SMS to {}: Your bag {} has been located. Please contact the baggage desk.".format(
        owner["phone"] or "(no phone on file)", tag_id
    )
    db.log_event(
        "mock_sms_sent",
        tag_id,
        "staff",
        "{}; source={}; recipient={}".format(message, source_id, owner["phone"] or "none"),
    )
    st.success(message)


def untagged_page():
    st.title("Match an untagged found bag")
    _reference_controls()
    with st.form("found_form"):
        weight = st.number_input("Found bag weight (kg)", min_value=0.1, value=18.0, step=0.1)
        length = st.number_input("Found bag length (cm)", min_value=1.0, value=67.0)
        width = st.number_input("Found bag width (cm)", min_value=1.0, value=43.0)
        height = st.number_input("Found bag height (cm)", min_value=1.0, value=25.0)
        photo = _capture_image("Photograph the found bag", "found")
        submitted = st.form_submit_button("Find candidates")
    if submitted:
        if not photo:
            st.error("Photograph or upload the found bag first.")
        elif st.session_state.get("reference_rgb") is None:
            st.error("Photograph the empty box reference before analyzing a bag.")
        else:
            try:
                result = analyze_bag(photo, st.session_state["reference_rgb"])
            except ValueError as error:
                st.error(str(error))
                return
            found_id = "FND-" + uuid.uuid4().hex[:8].upper()
            image_path = os.path.join(IMAGE_DIR, "{}.jpg".format(found_id.lower()))
            save_image(photo, image_path)
            rgb, lab = result["rgb"], result["lab"]
            item = {
                "found_id": found_id,
                "found_time": datetime.now().isoformat(timespec="seconds"),
                "weight_kg": weight,
                "length_cm": length,
                "width_cm": width,
                "height_cm": height,
                "r": rgb[0], "g": rgb[1], "b": rgb[2],
                "L": lab[0], "a": lab[1], "b_lab": lab[2],
                "colour_name": colour_name(rgb),
                "thumb_path": image_path,
                "status": "found",
                "matched_tag_id": None,
            }
            db.insert_untagged(item)
            db.log_event("found", found_id, "staff", "Untagged bag recorded")
            results = rank_bags(item, db.get_all_bags())
            st.session_state["active_found_id"] = found_id
            st.session_state["active_found_results"] = [
                {
                    "bag": dict(item["bag"]),
                    "score": item["score"],
                    "reasons": item["reasons"],
                }
                for item in results
            ]
            st.session_state["active_found_record"] = dict(item)
    found_id = st.session_state.get("active_found_id")
    found_record = st.session_state.get("active_found_record")
    if found_id and found_record:
        st.subheader("Found bag {}".format(found_id))
        if found_record["thumb_path"] and os.path.exists(found_record["thumb_path"]):
            st.image(found_record["thumb_path"], width=280)
        candidates = st.session_state.get("active_found_results", [])
        _show_ranked(candidates)
        if candidates:
            options = [item["bag"]["tag_id"] for item in candidates]
            selected = st.selectbox("Staff: confirm the owner", options, key="found_confirm")
            if st.button("Yes — retag bag and notify owner"):
                db.confirm_match(found_id, selected)
                db.log_event("match_confirmed", found_id, "staff", "Matched to {}".format(selected))
                qr_path = os.path.join(QR_DIR, "{}.png".format(found_id.lower()))
                os.makedirs(QR_DIR, exist_ok=True)
                qrcode.make(selected).save(qr_path)
                st.image(qr_path, caption="Replacement QR tag for {}".format(selected), width=220)
                _send_mock_sms(selected, found_id)
                st.session_state.pop("active_found_id", None)
                st.session_state.pop("active_found_record", None)
                st.session_state.pop("active_found_results", None)


def database_page():
    st.title("Database")
    datasets = {
        "Checked-in bags": [dict(row) for row in db.get_all_bags()],
        "Synthetic passengers": [dict(row) for row in db.get_all_passengers()],
        "Found untagged bags": [dict(row) for row in db.get_all_untagged()],
        "Lost reports": [dict(row) for row in db.get_lost_reports()],
    }
    dataset_name = st.selectbox("Dataset", list(datasets))
    data = pd.DataFrame(datasets[dataset_name])
    st.dataframe(data)
    if not data.empty:
        filename = dataset_name.lower().replace(" ", "_") + ".csv"
        csv = data.to_csv(index=False).encode("utf-8")
        st.download_button("Download {} CSV".format(dataset_name.lower()), csv, filename, "text/csv")
    st.subheader("Event log")
    events = db.get_events()
    st.dataframe(pd.DataFrame([dict(row) for row in events]))
    st.markdown("---")
    st.warning("Purge permanently deletes bags, contacts, reports, found items and events.")
    if st.checkbox("I understand this deletes all demo data", key="purge_confirm"):
        if st.button("Purge database"):
            db.purge_all()
            st.success("Database purged.")
            st.experimental_rerun()


def main():
    st.set_page_config(page_title="MatchABag", page_icon="🧳", layout="wide")
    theme.apply_theme();
    db.init_db()
    pages = {
        "Home": home_page,
        "Check-in": checkin_page,
        "Find my bag": find_bag_page,
        "Untagged bag": untagged_page,
        "Database": database_page,
    }
    selected = st.sidebar.radio("Navigation", list(pages))
    sync_bag_photos()
    pages[selected]()


if __name__ == "__main__":
    main()
