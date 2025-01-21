from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
from rembg import remove
from PIL import Image
import tempfile
from pymongo import MongoClient
import urllib.parse
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import bcrypt
import zipfile
import cv2
import numpy as np
import io
import logging
import traceback

app = Flask(__name__)

TEMP_DIR = "temp_images"
os.makedirs(TEMP_DIR, exist_ok=True)
# Enable CORS for the frontend domain (localhost:8080)
CORS(app, origins=["https://euphonious-gumption-3c4ce8.netlify.app"], methods=["GET", "POST", "OPTIONS"], allow_headers=["Content-Type", "Authorization"])

# Logging configuration
logging.basicConfig(level=logging.INFO)

# MongoDB configuration
username = "arshadusama074"
password = "Usamasial0012@"
encoded_username = urllib.parse.quote_plus(username)
encoded_password = urllib.parse.quote_plus(password)

try:
    client = MongoClient(f'mongodb+srv://{encoded_username}:{encoded_password}@cluster0.jrqck.mongodb.net/')
    db = client["user_auth"]
    messages_collection = db["messages"]
    logging.info("MongoDB connected successfully.")
    users_collection = db["user_authentications"]
except Exception as e:
    logging.error(f"Error connecting to MongoDB: {e}")
    raise

# Email configuration
EMAIL_ADDRESS = "arshadusama074@gmail.com"  # Your email
EMAIL_PASSWORD = "rsoh hisv hhgo tyty"  # Replace with your App Password

def send_email(name, email, message):
    try:
        # Create email content
        msg = MIMEMultipart()
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = EMAIL_ADDRESS
        msg["Subject"] = "New Contact Message"

        body = f"""
        Name: {name}
        Email: {email}
        Message: {message}
        """
        msg.attach(MIMEText(body, "plain"))

        # Send the email
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, EMAIL_ADDRESS, msg.as_string())

        logging.info("Email sent successfully.")
    except Exception as e:
        logging.error(f"Failed to send email: {e}")


@app.route('/remove-background', methods=['POST', 'OPTIONS'])
def remove_background():
    """Remove background from the uploaded image."""
    if request.method == 'OPTIONS':
        # Handling the preflight request
        response = app.make_response('')
        response.headers['Access-Control-Allow-Origin'] = 'https://euphonious-gumption-3c4ce8.netlify.app'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    if 'image' not in request.files:
        return {'error': 'No file uploaded'}, 400

    file = request.files['image']

    try:
        # Open the uploaded image
        input_image = Image.open(file.stream).convert("RGBA")

        # Remove the background using rembg
        output_image = remove(input_image)

        # Save the output image to a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
            output_image.save(temp_file.name, format="PNG")
            temp_file_path = temp_file.name

        # Send the processed image back to the client
        return send_file(
            temp_file_path,
            mimetype='image/png',
            as_attachment=True,
            download_name="background_removed.png"
        )

    except Exception as e:
        # Log the error and return an appropriate response
        print(f"Error: {e}")
        return {'error': 'An error occurred while processing the image'}, 500


@app.route('/contact', methods=['POST', 'OPTIONS'])
def contact():
    if request.method == 'OPTIONS':
        # Handling the preflight request
        response = app.make_response('')
        response.headers['Access-Control-Allow-Origin'] = 'https://euphonious-gumption-3c4ce8.netlify.app'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    try:
        data = request.json
        logging.info(f"Received payload: {data}")  # Debug log

        # Validate input
        name = data.get('name', '').strip()
        email = data.get('email', '').strip()
        message = data.get('message', '').strip()

        if not name or not email or not message:
            return jsonify({"success": False, "message": "All fields are required"}), 400

        # Save message to MongoDB
        messages_collection.insert_one({"name": name, "email": email, "message": message})
        logging.info("Message saved successfully.")

        # Send email
        send_email(name, email, message)

        return jsonify({"success": True, "message": "Message sent successfully!"}), 200

    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return jsonify({"success": False, "message": "An unexpected error occurred"}), 500


@app.route('/compress-image', methods=['POST', 'OPTIONS'])
def compress_image():
    if request.method == 'OPTIONS':
        # Handling the preflight request
        response = app.make_response('')
        response.headers['Access-Control-Allow-Origin'] = 'https://euphonious-gumption-3c4ce8.netlify.app'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    if 'image' not in request.files:
        return {'error': 'No file uploaded'}, 400

    file = request.files['image']

    # Read the uploaded image
    npimg = np.fromfile(file, np.uint8)
    image = cv2.imdecode(npimg, cv2.IMREAD_COLOR)

    if image is None:
        return {'error': 'Invalid image format'}, 400

    # Save the compressed image to a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
        compression_quality = 30  # Adjust for desired compression
        cv2.imwrite(temp_file.name, image, [cv2.IMWRITE_JPEG_QUALITY, compression_quality])
        temp_file_path = temp_file.name

    # Send the compressed file back to the client
    return send_file(temp_file_path, mimetype='image/jpeg', as_attachment=True, download_name="compressed_image.jpg")


@app.route('/login_user', methods=['POST', 'OPTIONS'])
def login_user():
    if request.method == 'OPTIONS':
        # Handling the preflight request
        response = app.make_response('')
        response.headers['Access-Control-Allow-Origin'] = 'https://euphonious-gumption-3c4ce8.netlify.app'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    data = request.json
    username = data.get('username')
    password = data.get('password')

    # Debugging - log incoming data
    print(f"Login attempt for username: {username}")

    # Print all users in the collection for debugging
    users = list(users_collection.find())
    print("Current users in database:")
    for user in users:
        print(user)

    # Check for user by email
    user = users_collection.find_one({"email": username})
    if not user:
        print("User not found!")  # Debugging message
        return jsonify({"success": False, "message": "User not found!"}), 404

    # Verify password
    if bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
        print(f"User {username} logged in successfully!")
        return jsonify({"success": True, "message": "Login successful!"}), 200
    else:
        print(f"Invalid password for user {username}")
        return jsonify({"success": False, "message": "Invalid password!"}), 401


@app.route('/register_user', methods=['POST', 'OPTIONS'])
def register_user():
    if request.method == 'OPTIONS':
        # Handling the preflight request
        response = app.make_response('')
        response.headers['Access-Control-Allow-Origin'] = 'https://euphonious-gumption-3c4ce8.netlify.app'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    """Register a new user."""
    try:
        data = request.get_json()
        name = data.get('name')
        email = data.get('email')
        password = data.get('password')

        if not name or not email or not password:
            return jsonify({"success": False, "message": "Missing required fields!"}), 400

        # Check if email already exists
        if users_collection.find_one({"email": email}):
            return jsonify({"success": False, "message": "User already exists!"}), 400

        # Hash the password
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        # Store user data
        user = {"name": name, "email": email, "password": hashed_password}
        users_collection.insert_one(user)

        return jsonify({"success": True, "message": f"User {name} registered successfully!"}), 201

    except Exception as e:
        print(f"Error occurred: {e}")
        return jsonify({"success": False, "message": "An error occurred while processing your request."}), 500
    
@app.route('/remove_backgrounds',methods=['POST', 'OPTIONS'])
def remove_backgrounds():
    if request.method == 'OPTIONS':
        # Handling the preflight request
        response = app.make_response('')
        response.headers['Access-Control-Allow-Origin'] = 'https://euphonious-gumption-3c4ce8.netlify.app'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    if 'image' not in request.files:
        return {'error': 'No files uploaded'}, 400

    files = request.files.getlist('image')

    if not files:
        return {'error': 'No files uploaded'}, 400

    # Create a temporary ZIP file to store processed images
    temp_zip_file = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    with zipfile.ZipFile(temp_zip_file.name, 'w') as zipf:
        for file in files:
            try:
                # Read the uploaded image
                npimg = np.fromfile(file, np.uint8)
                image = cv2.imdecode(npimg, cv2.IMREAD_UNCHANGED)

                if image is None:
                    continue

                # Remove the background
                output_image = remove(image)

                # Save the processed image to a temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
                    # Ensure the image is written in a correct format
                    cv2.imwrite(temp_file.name, output_image)

                    # Add processed image to the ZIP file
                    zipf.write(temp_file.name, arcname=file.filename)
                    os.unlink(temp_file.name)  # Delete temporary image file
            except Exception as e:
                print(f"Error processing file {file.filename}: {e}")

    # Send the zip file back to the client
    return send_file(temp_zip_file.name, mimetype='application/zip', as_attachment=True, download_name="background_removed_images.zip")

@app.route('/compress-imagess', methods=['POST', 'OPTIONS'])
def compress_imagess():
    if request.method == 'OPTIONS':
        # Handling the preflight request
        response = app.make_response('')
        response.headers['Access-Control-Allow-Origin'] = 'https://euphonious-gumption-3c4ce8.netlify.app'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    if 'images' not in request.files:
        return {'error': 'No files uploaded'}, 400

    files = request.files.getlist('images')

    if not files:
        return {'error': 'No files uploaded'}, 400

    temp_zip_file = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    with zipfile.ZipFile(temp_zip_file.name, 'w') as zipf:
        for file in files:
            try:
                # Read the uploaded image
                npimg = np.fromfile(file, np.uint8)
                image = cv2.imdecode(npimg, cv2.IMREAD_COLOR)

                if image is None:
                    continue

                # Save the compressed image to a temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
                    compression_quality = 30  # Adjust for desired compression
                    cv2.imwrite(temp_file.name, image, [cv2.IMWRITE_JPEG_QUALITY, compression_quality])
                    # Add compressed image to the zip file
                    zipf.write(temp_file.name, arcname=file.filename)
                    os.unlink(temp_file.name)
            except Exception as e:
                print(f"Error processing file {file.filename}: {e}")

    # Send the zip file back to the client
    return send_file(temp_zip_file.name, mimetype='application/zip', as_attachment=True, download_name="compressed_images.zip")
@app.route('/batch-crop-and-compress', methods=['POST', 'OPTIONS'])
def batch_crop_and_compress():
    if request.method == 'OPTIONS':
        # Handling the preflight request
        response = app.make_response('')
        response.headers['Access-Control-Allow-Origin'] = 'https://euphonious-gumption-3c4ce8.netlify.app'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    if 'images' not in request.files:
        return {'error': 'No files uploaded'}, 400

    files = request.files.getlist('images')

    if not files:
        return {'error': 'No files uploaded'}, 400

    # Parse cropping dimensions from the request
    try:
        crop_x = int(request.form.get('crop_x', 0))
        crop_y = int(request.form.get('crop_y', 0))
        crop_width = int(request.form.get('crop_width', 100))
        crop_height = int(request.form.get('crop_height', 100))
    except ValueError:
        return {'error': 'Invalid crop dimensions provided'}, 400

    # Create a temporary zip file
    temp_zip_file = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    zipf = zipfile.ZipFile(temp_zip_file.name, 'w', zipfile.ZIP_DEFLATED)

    try:
        for file in files:
            try:
                # Read the uploaded image
                npimg = np.fromfile(file, np.uint8)
                image = cv2.imdecode(npimg, cv2.IMREAD_COLOR)

                if image is None:
                    continue

                # Validate crop dimensions against the image size
                h, w, _ = image.shape
                if crop_x + crop_width > w or crop_y + crop_height > h or crop_width <= 0 or crop_height <= 0:
                    continue  # Skip if crop dimensions are invalid

                # Perform the cropping
                cropped_image = image[crop_y:crop_y + crop_height, crop_x:crop_x + crop_width]

                # Create a temporary file for the cropped and compressed image
                with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
                    compression_quality = 30  # Adjust for desired compression
                    cv2.imwrite(temp_file.name, cropped_image, [cv2.IMWRITE_JPEG_QUALITY, compression_quality])

                    # Add cropped and compressed image to the zip file
                    zipf.write(temp_file.name, arcname=os.path.basename(file.filename))  # Ensure correct filename in the zip
                    os.remove(temp_file.name)  # Clean up temporary file after adding it to the ZIP
            except Exception as e:
                print(f"Error processing file {file.filename}: {e}")

    finally:
        zipf.close()

    # Send the zip file back to the client
    return send_file(temp_zip_file.name, mimetype='application/zip', as_attachment=True, download_name="cropped_and_compressed_images.zip")

if __name__ == '__main__':
    # Run the Flask app on port 5000
    app.run(debug=True, port=5000)
