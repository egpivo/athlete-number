import requests
import streamlit as st
from PIL import Image

st.set_page_config(
    page_title="Bib Number Detection",
    page_icon="🧑‍💻",
    layout="wide",
    initial_sidebar_state="expanded",
)


def send_images_to_api(images):
    """Send batch images to the API for processing and return detected bib numbers."""
    api_url = "http://localhost:5566/extract/bib-numbers"  # Updated API URL
    files = [("files", (img.name, img.getvalue(), "image/jpeg")) for img in images]
    response = requests.post(api_url, files=files)

    if response.status_code == 200:
        return response.json()
    else:
        return {
            "error": "Failed to get a response from the API.",
            "status_code": response.status_code,
        }


st.write("Upload images to detect bib numbers.")

uploaded_files = st.file_uploader(
    "Choose images...", type=["jpg", "jpeg", "png"], accept_multiple_files=True
)

if uploaded_files:
    if st.button("Detect Bib Numbers"):
        st.write("Processing...")
        response = send_images_to_api(uploaded_files)

        if "error" in response:
            st.error(f"{response['error']} (Status Code: {response['status_code']})")
        else:
            for uploaded_file in uploaded_files:
                image = Image.open(uploaded_file)
                matching_result = next(
                    (res for res in response if res["filename"] == uploaded_file.name),
                    None,
                )

                col1, col2 = st.columns([1, 1])
                with col1:
                    st.image(
                        image,
                        caption=f"Uploaded: {uploaded_file.name}",
                        use_container_width=True,
                    )

                with col2:
                    if matching_result:
                        bib_number = matching_result.get(
                            "athlete_numbers", ["Not detected"]
                        )
                        st.write(
                            f"**Detected Bib Number:** {', '.join(map(str, bib_number))}"
                        )
                        st.json(matching_result)  # Display full JSON response
                    else:
                        st.warning(f"No result found for {uploaded_file.name}.")
