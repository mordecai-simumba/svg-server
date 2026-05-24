from flask import Flask, request, jsonify
from flask_cors import CORS

import cv2
import numpy as np
import os
import uuid
import gc

app = Flask(__name__)
CORS(app)

# =========================================================
# FOLDERS
# =========================================================

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# =========================================================
# IMAGE TO SVG ENGINE
# =========================================================

def image_to_svg(image_path, svg_path):

    # =====================================================
    # LOAD IMAGE IN GRAYSCALE
    # =====================================================

    image = cv2.imread(
        image_path,
        cv2.IMREAD_GRAYSCALE
    )

    if image is None:
        raise Exception("Failed to load image")

    # =====================================================
    # RESIZE INSIDE SERVER
    # REDUCES RAM MASSIVELY
    # =====================================================

    max_width = 600

    height, width = image.shape

    if width > max_width:

        ratio = max_width / width

        new_height = int(height * ratio)

        image = cv2.resize(
            image,
            (max_width, new_height)
        )

    # =====================================================
    # LIGHT BLUR
    # =====================================================

    image = cv2.GaussianBlur(
        image,
        (3, 3),
        0
    )

    # =====================================================
    # THRESHOLD
    # =====================================================

    _, thresh = cv2.threshold(
        image,
        180,
        255,
        cv2.THRESH_BINARY_INV
    )

    # =====================================================
    # LIGHT MORPHOLOGY
    # =====================================================

    kernel = np.ones((2, 2), np.uint8)

    thresh = cv2.morphologyEx(
        thresh,
        cv2.MORPH_OPEN,
        kernel
    )

    # =====================================================
    # FIND CONTOURS
    # =====================================================

    contours, _ = cv2.findContours(
        thresh,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    # =====================================================
    # SVG SETUP
    # =====================================================

    height, width = image.shape

    svg = f'''
<svg xmlns="http://www.w3.org/2000/svg"
 width="{width}"
 height="{height}"
 viewBox="0 0 {width} {height}">

<defs>

<filter id="shadow">
    <feDropShadow
        dx="1"
        dy="1"
        stdDeviation="1"
        flood-color="#777777"
        flood-opacity="0.25"/>
</filter>

</defs>
'''

    # =====================================================
    # DRAW CONTOURS
    # =====================================================

    for contour in contours:

        area = cv2.contourArea(contour)

        # =================================================
        # REMOVE SMALL NOISE
        # =================================================

        if area < 60:
            continue

        # =================================================
        # SMOOTH SHAPES
        # =================================================

        epsilon = (
            0.003 *
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
        # MAIN SVG PATH
        # =================================================

        path = "M "

        for point in contour:

            x, y = point[0]

            path += f"{x},{y} "

        path += "Z"

        # =================================================
        # LIGHT SHADOW PATH
        # =================================================

        shadow_path = "M "

        for point in contour:

            x, y = point[0]

            shadow_path += f"{x+1},{y+1} "

        shadow_path += "Z"

        # =================================================
        # SHADOW
        # =================================================

        svg += f'''
<path
 d="{shadow_path}"
 fill="none"
 stroke="#888888"
 stroke-width="1"
 opacity="0.18"/>
'''

        # =================================================
        # MAIN VECTOR
        # =================================================

        svg += f'''
<path
 d="{path}"
 fill="none"
 stroke="black"
 stroke-width="1.6"
 stroke-linecap="round"
 stroke-linejoin="round"
 filter="url(#shadow)"/>
'''

    # =====================================================
    # SVG END
    # =====================================================

    svg += "\n</svg>"

    # =====================================================
    # SAVE SVG
    # =====================================================

    with open(
        svg_path,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(svg)


# =========================================================
# HOME ROUTE
# =========================================================

@app.route("/")
def home():

    return "Smart Lightweight SVG Server Running"


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

        # =================================================
        # GENERATE SVG
        # =================================================

        image_to_svg(
            input_path,
            output_path
        )

        # =================================================
        # READ SVG
        # =================================================

        with open(
            output_path,
            "r",
            encoding="utf-8"
        ) as f:

            svg_text = f.read()

        # =================================================
        # CLEANUP
        # =================================================

        if os.path.exists(input_path):
            os.remove(input_path)

        if os.path.exists(output_path):
            os.remove(output_path)

        gc.collect()

        # =================================================
        # RESPONSE
        # =================================================

        return jsonify({
            "success": True,
            "svg": svg_text
        })

    except Exception as e:

        # Cleanup even on failure
        try:

            if os.path.exists(input_path):
                os.remove(input_path)

            if os.path.exists(output_path):
                os.remove(output_path)

        except:
            pass

        gc.collect()

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# =========================================================
# START SERVER
# =========================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=8080
    )