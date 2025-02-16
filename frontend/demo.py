import gc  # Garbage collection
import os
import uuid  # Generate unique key to reset file uploader

import requests
import streamlit as st
from PIL import Image

st.set_page_config(
    page_title="InstAI Bib Number Detection",
    page_icon="https://cdn.prod.website-files.com/66da7c1fe1ca90cace840157/66e661001167498ba9c12619_thumbnail2.png",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize session state for uploaded files, results, and file uploader key
if "uploaded_files" not in st.session_state:
    st.session_state.uploaded_files = None

if "detection_results" not in st.session_state:
    st.session_state.detection_results = None

if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = str(uuid.uuid4())  # Generate a unique key


def send_images_to_api(images):
    """Send batch images to the API for processing and return detected bib numbers."""
    api_url = os.getenv("BACKEND_URL", "http://localhost:5566") + "/extract/bib-numbers"
    files = [("files", (img.name, img.getvalue(), "image/jpeg")) for img in images]
    response = requests.post(api_url, files=files)

    if response.status_code == 200:
        return response.json()
    else:
        return {
            "error": "Failed to get a response from the API.",
            "status_code": response.status_code,
        }


def cleanup_gpu_on_backend():
    """Sends a request to backend to clean GPU memory."""
    api_url = os.getenv("BACKEND_URL", "http://localhost:5566") + "/cleanup-gpu"
    requests.post(api_url)


st.title("InstAI Bib Number Detection")
st.write("Upload images to detect bib numbers.")

# File uploader (resets when "Clear All" is clicked)
uploaded_files = st.file_uploader(
    "Choose images...",
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=True,
    key=st.session_state.uploader_key,  # Unique key forces reset
)

# Store uploaded files in session state
if uploaded_files:
    st.session_state.uploaded_files = uploaded_files

# Arrange buttons: "Detect" (left) and "Clear" (rightmost)
col_left, col_rightmost = st.columns([4, 1])  # Left button wider, rightmost smaller

with col_left:
    if st.session_state.uploaded_files and st.button("Detect Bib Numbers"):
        st.write("Processing...")
        st.session_state.detection_results = send_images_to_api(
            st.session_state.uploaded_files
        )

        # 🔥 After detection, trigger GPU cleanup
        cleanup_gpu_on_backend()

with col_rightmost:
    if st.button("Clear All"):
        st.session_state.uploaded_files = None  # Reset uploaded files
        st.session_state.detection_results = None  # Clear results
        st.session_state.uploader_key = str(uuid.uuid4())  # Reset uploader
        gc.collect()  # Free CPU memory
        st.rerun()  # Refresh UI

# Display detection results in full width
if st.session_state.detection_results and st.session_state.uploaded_files:
    for uploaded_file in st.session_state.uploaded_files:
        image = Image.open(uploaded_file)
        matching_result = next(
            (
                res
                for res in st.session_state.detection_results
                if res["filename"] == uploaded_file.name
            ),
            None,
        )

        col1, col2 = st.columns([1, 2])  # Full width for results
        with col1:
            st.image(
                image,
                caption=f"Uploaded: {uploaded_file.name}",
                use_container_width=True,
            )

        with col2:
            if matching_result:
                bib_number = matching_result.get("athlete_numbers", ["Not detected"])
                st.write(f"**Detected Bib Number:** {', '.join(map(str, bib_number))}")
                st.json(matching_result)  # Show full JSON response
            else:
                st.warning(f"No result found for {uploaded_file.name}.")
