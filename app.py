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