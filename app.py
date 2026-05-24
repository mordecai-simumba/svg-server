from flask import Flask, request, jsonify
import cv2
import numpy as np
import os
import uuid

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


def image_to_svg(image_path, svg_path):

    # Read image
    image = cv2.imread(image_path)

    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Edge detection
    edges = cv2.Canny(gray, 100, 200)

    # Find contours
    contours, _ = cv2.findContours(
        edges,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    height, width = edges.shape

    # Begin SVG
    svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg"
 width="{width}"
 height="{height}"
 viewBox="0 0 {width} {height}">
'''

    # Convert contours to SVG paths
    for contour in contours:

        if len(contour) < 3:
            continue

        path = "M "

        for point in contour:
            x, y = point[0]
            path += f"{x},{y} "

        path += "Z"

        svg_content += f'''
<path d="{path}"
 fill="none"
 stroke="black"
 stroke-width="1"/>
'''

    svg_content += "</svg>"

    # Save SVG
    with open(svg_path, "w") as f:
        f.write(svg_content)


@app.route("/convert", methods=["POST"])
def convert():

    if "image" not in request.files:
        return jsonify({
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

        image_to_svg(input_path, output_path)

        with open(output_path, "r") as f:
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


@app.route("/")
def home():
    return "Real SVG Blueprint Server Running"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)