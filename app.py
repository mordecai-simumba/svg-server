from flask import Flask, request, jsonify
from flask_cors import CORS
import subprocess
import uuid
import os

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

@app.route("/")
def home():
    return "SVG Server Running"

@app.route("/trace", methods=["POST"])
def trace_image():

    if "image" not in request.files:
        return jsonify({
            "success": False,
            "error": "No image uploaded"
        }), 400

    image = request.files["image"]

    uid = str(uuid.uuid4())

    input_path = f"{UPLOAD_FOLDER}/{uid}.png"

    temp_svg = f"{OUTPUT_FOLDER}/{uid}_temp.svg"

    output_path = f"{OUTPUT_FOLDER}/{uid}.svg"

    image.save(input_path)

    try:

        # STEP 1
        # Create initial SVG wrapper

        command1 = [
            "inkscape",
            input_path,
            "--export-type=svg",
            "--export-filename=" + temp_svg
        ]

        subprocess.run(command1, check=True)

        # STEP 2
        # Read SVG content

        with open(temp_svg, "r", encoding="utf-8") as f:
            svg_content = f.read()

        # DEBUG LOG
        print(svg_content[:500])

        # Return SVG

        return jsonify({
            "success": True,
            "svg": svg_content
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)