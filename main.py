from flask import Flask, request, jsonify
from flask_cors import CORS
import jwt, datetime, os
import supabase
from werkzeug.utils import secure_filename
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import tempfile

app = Flask(__name__)
CORS(app)

app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev_secret")

# Supabase setup
supabase_client = supabase.create_client(
    os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"]
)

# Google Drive setup
creds = service_account.Credentials.from_service_account_file(
    "service_account.json", scopes=["https://www.googleapis.com/auth/drive.file"]
)
drive_service = build("drive", "v3", credentials=creds)
DRIVE_FOLDER_ID = os.environ["DRIVE_FOLDER_ID"]

ADMIN_USER = os.environ.get("ADMIN_USER")
ADMIN_PASS = os.environ.get("ADMIN_PASS")

def token_required(f):
    def wrapper(*args, **kwargs):
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if not token:
            return jsonify({"error": "Token is missing"}), 401
        try:
            jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
        except:
            return jsonify({"error": "Invalid token"}), 401
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json()
    if data["username"] == ADMIN_USER and data["password"] == ADMIN_PASS:
        token = jwt.encode(
            {"user": ADMIN_USER, "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=2)},
            app.config["SECRET_KEY"], algorithm="HS256"
        )
        return jsonify({"token": token})
    return jsonify({"error": "Invalid credentials"}), 401

@app.route("/api/products", methods=["GET"])
def get_products():
    res = supabase_client.table("products").select("*").execute()
    return jsonify(res.data)

@app.route("/api/products", methods=["POST"])
@token_required
def add_product():
    name = request.form["name"]
    price = request.form["price"]
    sizes = request.form["sizes"]
    description = request.form["description"]
    image = request.files["image"]

    # Save temp file for upload
    temp_file = tempfile.NamedTemporaryFile(delete=False)
    image.save(temp_file.name)
    file_metadata = {"name": secure_filename(image.filename), "parents": [DRIVE_FOLDER_ID]}
    media = MediaFileUpload(temp_file.name, mimetype=image.mimetype)
    uploaded = drive_service.files().create(body=file_metadata, media_body=media, fields="id").execute()
    drive_service.permissions().create(fileId=uploaded["id"], body={"role": "reader", "type": "anyone"}).execute()
    image_url = f"https://drive.google.com/uc?id={uploaded['id']}"

    supabase_client.table("products").insert({
        "name": name, "price": price, "sizes": sizes, "description": description, "image_url": image_url
    }).execute()
    return jsonify({"message": "Product added"})

@app.route("/api/products/<id>", methods=["DELETE"])
@token_required
def delete_product(id):
    supabase_client.table("products").delete().eq("id", id).execute()
    return jsonify({"message": "Deleted"})

if __name__ == "__main__":
    app.run(debug=True)
