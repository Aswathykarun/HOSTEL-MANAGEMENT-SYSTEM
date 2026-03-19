from flask import Flask, render_template, request, jsonify
from pymongo import MongoClient

app = Flask(__name__)

# MongoDB connection
client = MongoClient("mongodb://localhost:27017/")
mongo_db = client["hostel_db"]

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/admin")
def admin():
    return render_template("admin.html")

@app.route("/warden")
def warden():
    return render_template("warden.html")

@app.route("/student")
def student():
    return render_template("student.html")


# Mongo collection
notices = mongo_db["notices"]

@app.route("/add_notice", methods=["POST"])
def add_notice():
    data = request.json
    notices.insert_one({
        "message": data["message"]
    })
    return jsonify({"status": "success"})


if __name__ == "__main__":
    app.run(debug=True)