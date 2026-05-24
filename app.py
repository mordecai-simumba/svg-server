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
# SVG ENGINE
# =========================================================

def image_to_svg(image_path, svg_path):

    image = cv2.imread(image_path)

    if image is None:
        raise Exception("Failed to read image")

    # =====================================================
    # GRAYSCALE
    # =====================================================

    gray = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY
    )

    # =====================================================
    # BLUR (REDUCE NOISE)
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
    # CONTOUR DETECTION ONLY
    # =====================================================

    contours, hierarchy = cv2.findContours(
        cleaned,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_TC89_KCOS
    )

    for contour in contours:

        area = cv2.contourArea(contour)

        # =================================================
        # REMOVE TINY NOISE
        # =================================================

        if area < 80:
            continue

        # =================================================
        # SIMPLIFY CONTOUR
        # =================================================

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

        # =================================================
        # MAIN PATH
        # =================================================

        path = "M "

        for point in contour:

            x, y = point[0]

            path += f"{x},{y} "

        path += "Z"

        # =================================================
        # SHADOW PATH (PSEUDO 3D)
        # =================================================

        shadow_path = "M "

        for point in contour:

            x, y = point[0]

            shadow_path += f"{x+2},{y+2} "

        shadow_path += "Z"

        # =================================================
        # SHADOW LAYER
        # =================================================

        svg_content += f'''
<path
    d="{shadow_path}"
    fill="none"
    stroke="#888888"
    stroke-width="2"
    opacity="0.25"
    stroke-linejoin="round"/>
'''

        # =================================================
        # MAIN VECTOR PATH
        # =================================================

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
    # SVG FOOTER
    # =====================================================

    svg_content += "\n</svg>"

    # =====================================================
    # SAVE SVG
    # =====================================================

    with open(svg_path, "w", encoding="utf-8") as f:

        f.write(svg_content)


# =========================================================
# CONVERT ROUTE
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