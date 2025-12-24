"""
Simple Streamlit UI for CLIP Image Search API.

Shows a query box, connects to the API for health, and displays
top-k image results with similarity scores.
"""

import os
import time
from typing import Optional
from io import BytesIO

import requests
import streamlit as st
from PIL import Image


# Configuration (env overrides, sensible defaults for local dev)
API_HOST = os.getenv("API_HOST", "localhost")
API_PORT = os.getenv("API_PORT", "8000")
API_URL = f"http://{API_HOST}:{API_PORT}"


st.set_page_config(
    page_title="Visual Cortex Search",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("Visual Cortex - Image Search")
st.caption(f"API: {API_URL}")


# Sidebar: Health + controls
st.sidebar.header("Configuration")
top_k = st.sidebar.slider("Number of results", min_value=1, max_value=50, value=10)

st.sidebar.markdown("---")
health_data = None
try:
    resp = requests.get(f"{API_URL}/health", timeout=5)
    if resp.status_code == 200:
        health_data = resp.json()
        st.sidebar.success("API Connected")
        st.sidebar.caption(f"Model: {health_data.get('model', 'N/A')}")
        st.sidebar.caption(f"Device: {health_data.get('device', 'N/A')}")
        st.sidebar.caption(f"Images: {health_data.get('num_images', 'N/A')}")
    else:
        st.sidebar.warning(f"Health check failed ({resp.status_code})")
except Exception as e:
    st.sidebar.error(f"API Connection Failed: {e}")


st.markdown("---")

# Query controls
col1, col2 = st.columns([4, 1])
with col1:
    query = st.text_input(
        "Enter your search query:",
        placeholder="e.g., 'a red car on a sunny day'",
        label_visibility="collapsed",
    )
with col2:
    search_button = st.button("🔍 Search", use_container_width=True)

st.markdown("---")


def fetch_image_bytes(url: str, timeout: int = 15) -> Optional[bytes]:
    """Fetch image bytes from URL."""
    try:
        r = requests.get(url, timeout=timeout)
        r.raise_for_status()
        return r.content
    except Exception:
        return None


def resize_image_square(img_bytes: bytes, size: int = 300) -> Optional[bytes]:
    """Resize image to square (same width/height) and return as bytes."""
    try:
        img = Image.open(BytesIO(img_bytes))
        # Convert to RGB if needed (e.g., RGBA, grayscale)
        if img.mode != "RGB":
            img = img.convert("RGB")
        # Resize to square
        img_resized = img.resize((size, size), Image.Resampling.LANCZOS)
        # Return as bytes
        output = BytesIO()
        img_resized.save(output, format="JPEG", quality=85)
        return output.getvalue()
    except Exception:
        return None


# Execute search
if search_button and query:
    spinner_msg = f"Searching for '{query}'..."
    timeout_val = 30

    with st.spinner(spinner_msg):
        start = time.time()
        try:
            resp = requests.post(
                f"{API_URL}/search",
                json={
                    "query": query,
                    "top_k": top_k,
                },
                timeout=timeout_val,
            )
        except requests.exceptions.Timeout:
            st.error("Request timeout. The API took too long to respond.")
            resp = None
        except requests.exceptions.ConnectionError:
            st.error(f"Cannot connect to API at {API_URL}")
            resp = None
        except Exception as e:
            st.error(f"Error: {e}")
            resp = None

        elapsed = time.time() - start

        if not resp:
            st.info("No response from API.")
        elif resp.status_code != 200:
            # Show error from API
            try:
                data = resp.json()
                detail = data.get("detail") or data.get("error") or str(data)
            except Exception:
                detail = resp.text
            st.error(f"Search failed ({resp.status_code}): {detail}")
        else:
            results = resp.json()
            total = results.get("total_results", 0)
            st.success(f"Found {total} results in {elapsed:.2f}s")

            if total > 0:
                results_list = results.get("results", [])
                # Create rows of 3 columns each
                for row_idx in range(0, len(results_list), 3):
                    cols = st.columns(3, gap="medium")
                    for col_idx, col in enumerate(cols):
                        item_idx = row_idx + col_idx
                        if item_idx < len(results_list):
                            item = results_list[item_idx]
                            with col:
                                filename = item.get("filename")
                                score = float(item.get("similarity", 0.0))
                                img_url = f"{API_URL}/images/{filename}"
                                img_bytes = fetch_image_bytes(img_url)
                                if img_bytes:
                                    # Resize to square (300x300) for uniform display
                                    square_bytes = resize_image_square(img_bytes, size=300)
                                    if square_bytes:
                                        st.image(square_bytes, caption=filename, width=300)
                                        st.metric("Similarity", f"{score:.4f}")
                                    else:
                                        st.image(img_bytes, caption=filename, width=300)
                                        st.metric("Similarity", f"{score:.4f}")
                                else:
                                    st.warning(f"Could not load: {filename}")


st.markdown("---")
st.write("Tip: Set API_HOST and API_PORT environment variables if your API is not on localhost:8000.")

