from flask import Flask, request, jsonify
from flask_cors import CORS

import cv2
import numpy as np
import os
import uuid

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


# =========================================================
# MAIN SVG ENGINE
# =========================================================

def image_to_svg(image_path, svg_path):

    image = cv2.imread(image_path)

    if image is None:
        raise Exception("Failed to read image")

    original = image.copy()

    gray = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY
    )

    # =====================================================
    # NOISE REDUCTION
    # =====================================================

    blur = cv2.GaussianBlur(
        gray,
        (5, 5),
        0
    )

    # =====================================================
    # ADAPTIVE THRESHOLD
    # =====================================================

    thresh = cv2.adaptiveThreshold(
        blur,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        11,
        2
    )

    # =====================================================
    # MORPHOLOGICAL CLEANUP
    # =====================================================

    kernel = np.ones((2, 2), np.uint8)

    cleaned = cv2.morphologyEx(
        thresh,
        cv2.MORPH_CLOSE,
        kernel
    )

    height, width = cleaned.shape

    # =====================================================
    # SVG HEADER
    # =====================================================

    svg_content = f'''
<svg xmlns="http://www.w3.org/2000/svg"
 width="{width}"
 height="{height}"
 viewBox="0 0 {width} {height}">

<defs>

<filter id="shadow">
    <feDropShadow
        dx="2"
        dy="2"
        stdDeviation="2"
        flood-color="#888888"
        flood-opacity="0.35"/>
</filter>

</defs>
'''

    # =====================================================
    # LINE DETECTION
    # =====================================================

    lines = cv2.HoughLinesP(
        cleaned,
        1,
        np.pi / 180,
        threshold=80,
        minLineLength=50,
        maxLineGap=10
    )

    if lines is not None:

        for line in lines:

            x1, y1, x2, y2 = line[0]

            svg_content += f'''
<line
    x1="{x1}"
    y1="{y1}"
    x2="{x2}"
    y2="{y2}"
    stroke="black"
    stroke-width="2"
    stroke-linecap="round"
    opacity="0.95"/>
'''

    # =====================================================
    # CONTOUR DETECTION
    # =====================================================

    contours, hierarchy = cv2.findContours(
        cleaned,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_TC89_KCOS
    )

    for contour in contours:

        area = cv2.contourArea(contour)

        # ================================================
        # REMOVE NOISE
        # ================================================

        if area < 80:
            continue

        # ================================================
        # CONTOUR SIMPLIFICATION
        # ================================================

        epsilon = (
            0.002 *
            cv2.arcLength(contour, True)
        )

        contour = cv2.approxPolyDP(
            contour,
            epsilon,
            True
        )

        if len(contour) < 3:
            continue

        # ================================================
        # BUILD SVG PATH
        # ================================================

        path = "M "

        for point in contour:

            x, y = point[0]

            path += f"{x},{y} "

        path += "Z"

        # ================================================
        # SHADOW / 3D EFFECT
        # ================================================

        shadow_path = "M "

        for point in contour:

            x, y = point[0]

            shadow_path += f"{x+3},{y+3} "

        shadow_path += "Z"

        svg_content += f'''
<path
    d="{shadow_path}"
    fill="none"
    stroke="#888888"
    stroke-width="2"
    opacity="0.25"
    stroke-linejoin="round"/>
'''

        # ================================================
        # MAIN PATH
        # ================================================

        svg_content += f'''
<path
    d="{path}"
    fill="none"
    stroke="black"
    stroke-width="2"
    stroke-linecap="round"
    stroke-linejoin="round"
    filter="url(#shadow)"/>
'''

    # =====================================================
    # GRID DETECTION
    # =====================================================

    horizontal_kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (40, 1)
    )

    vertical_kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (1, 40)
    )

    horizontal_lines = cv2.morphologyEx(
        cleaned,
        cv2.MORPH_OPEN,
        horizontal_kernel
    )

    vertical_lines = cv2.morphologyEx(
        cleaned,
        cv2.MORPH_OPEN,
        vertical_kernel
    )

    # =====================================================
    # HORIZONTAL GRID LINES
    # =====================================================

    h_contours, _ = cv2.findContours(
        horizontal_lines,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    for contour in h_contours:

        x, y, w, h = cv2.boundingRect(contour)

        if w < 100:
            continue

        svg_content += f'''
<line
    x1="{x}"
    y1="{y}"
    x2="{x+w}"
    y2="{y}"
    stroke="#BBBBBB"
    stroke-width="1"
    opacity="0.45"/>
'''

    # =====================================================
    # VERTICAL GRID LINES
    # =====================================================

    v_contours, _ = cv2.findContours(
        vertical_lines,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    for contour in v_contours:

        x, y, w, h = cv2.boundingRect(contour)

        if h < 100:
            continue

        svg_content += f'''
<line
    x1="{x}"
    y1="{y}"
    x2="{x}"
    y2="{y+h}"
    stroke="#BBBBBB"
    stroke-width="1"
    opacity="0.45"/>
'''

    # =====================================================
    # SVG FOOTER
    # =====================================================

    svg_content += "\n</svg>"

    # =====================================================
    # SAVE SVG
    # =====================================================

    with open(svg_path, "w", encoding="utf-8") as f:

        f.write(svg_content)


# =========================================================
# API ROUTE
# =========================================================

@app.route("/convert", methods=["POST"])
def convert():

    if "image" not in request.files:

        return jsonify({
            "success": False,
            "error": "No image uploaded"
        }), 400

    image_file = request.files["image"]

    unique_id = str(uuid.uuid4())

    input_path = os.path.join(
        UPLOAD_FOLDER,
        unique_id + ".png"
    )

    output_path = os.path.join(
        OUTPUT_FOLDER,
        unique_id + ".svg"
    )

    image_file.save(input_path)

    try:

        image_to_svg(
            input_path,
            output_path
        )

        with open(
            output_path,
            "r",
            encoding="utf-8"
        ) as f:

            svg_text = f.read()

        return jsonify({
            "success": True,
            "svg": svg_text
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# =========================================================
# HOME ROUTE
# =========================================================

@app.route("/")
def home():

    return "Advanced SVG Blueprint Server Running"


# =========================================================
# START SERVER
# =========================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=8080
    )