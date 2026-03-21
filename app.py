from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import mysql.connector
from pymongo import MongoClient
from datetime import date, datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = "super_secret_key"

# ------------------ DATABASE CONNECTIONS ------------------

# MySQL (for hostel data)
mysql_conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="sql@4545",
    database="hostel_db",
    autocommit=True
)
# MongoDB (for notices + users)
mongo_client = MongoClient("mongodb://localhost:27017/")
mongo_db = mongo_client["hostel_db"]
notices_collection = mongo_db["notices"]
users_collection = mongo_db["users"]   # ✅ FIXED


# ------------------ AUTHENTICATION DECORATOR ------------------
def login_required(allowed_roles=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user' not in session:
                flash("Please log in to access this page.", "error")
                return redirect('/login')
            if allowed_roles and session.get('role') not in allowed_roles:
                flash("Unauthorized access to this section.", "error")
                return redirect(f"/{session.get('role')}")
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# ------------------ ROUTES ------------------

# ✅ HOME PAGE
@app.route('/')
def index():
    return render_template("index.html")


# ------------------ LOGIN ------------------

# ✅ LOGIN PAGE (GET)
@app.route('/login', methods=['GET'])
def login_page():
    return render_template("login.html")


# ✅ LOGIN LOGIC (POST)
@app.route('/login', methods=['POST'])
def login():
    session.clear()
    username = request.form['username']
    password = request.form['password']

    user = users_collection.find_one({
        "username": username,
        "password": password
    })

    if user:
        role = user['role']
        session['user'] = username
        session['role'] = role
        
        # In case the user document has a linked student_id (like '101')
        if 'student_id' in user:
            session['student_id'] = user['student_id']

        if role == 'admin':
            return redirect('/admin')
        elif role == 'warden':
            return redirect('/warden')
        elif role == 'student':
            return redirect('/student')

    flash("Invalid username or password.", "error")
    return redirect('/login')


# ------------------ STUDENT DASHBOARD ------------------

@app.route('/student')
@login_required(allowed_roles=['student'])
def student_dashboard():
    cursor = mysql_conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM hostel")
    hostels = cursor.fetchall()

    notices = list(notices_collection.find({}, {"_id": 0}))

    return render_template("student.html", hostels=hostels, notices=notices)


# ------------------ STUDENT MANAGEMENT ------------------

# ✅ VIEW ALL STUDENTS
@app.route('/students')
@login_required(allowed_roles=['admin', 'warden'])
def view_students():
    cursor = mysql_conn.cursor()

    cursor.execute("""
        SELECT 
            s.student_id, 
            s.student_name, 
            s.year_of_study,
            s.contact_number, 
            s.address,
            h.hostel_name,
            r.room_number
        FROM student s
        LEFT JOIN hostel h ON s.hostel_id = h.hostel_id
        LEFT JOIN room_allocation ra 
            ON s.student_id = ra.student_id
            AND ra.allocation_id = (
                SELECT MAX(allocation_id)
                FROM room_allocation
                WHERE student_id = s.student_id
            )
        LEFT JOIN room r ON ra.room_id = r.room_id
    """)
    students = cursor.fetchall()

    return render_template("manage_students.html", students=students)


# ✅ ADD STUDENT
@app.route('/add_student', methods=['POST'])
@login_required(allowed_roles=['admin'])
def add_student():
    name = request.form['name']
    year = request.form['year']
    contact = request.form['contact']
    address = request.form['address']
    dept_id = request.form['dept_id']
    hostel_id = request.form['hostel_id']

    cursor = mysql_conn.cursor()

    query = """
        INSERT INTO student
        (student_name, year_of_study, contact_number, address, department_id, hostel_id)
        VALUES (%s, %s, %s, %s, %s, %s)
    """

    try:
        cursor.execute(query, (name, year, contact, address, dept_id, hostel_id))
        mysql_conn.commit()
        flash("Student added successfully!", "success")
    except mysql.connector.IntegrityError as err:
        if 'department_ibfk' in err.msg or 'department_id' in err.msg or 'department' in err.msg:
            flash("Invalid Department ID: The specified department does not exist.", "error")
        elif 'hostel_ibfk' in err.msg or 'hostel_id' in err.msg or 'hostel' in err.msg:
            flash("Invalid Hostel ID: The specified hostel does not exist.", "error")
        else:
            flash(f"Data Integrity Error: A record with this data already exists or is invalid.", "error")
    except mysql.connector.Error as err:
        flash(f"Database Error: {err.msg}", "error")

    return redirect('/students')


# ✅ DELETE STUDENT
@app.route('/delete_student/<int:id>')
@login_required(allowed_roles=['admin'])
def delete_student(id):
    cursor = mysql_conn.cursor()

    cursor.execute("DELETE FROM student WHERE student_id = %s", (id,))
    mysql_conn.commit()

    return redirect('/students')


# ------------------ OTHER PAGES ------------------

@app.route('/view_hostels')
@login_required(allowed_roles=['admin'])
def view_hostels():
    return "<h2>All Hostels Page (Create HTML later)</h2>"


@app.route('/my_room')
@login_required(allowed_roles=['student'])
def my_room():
    return "<h2>My Room Page (Connect to DB later)</h2>"


@app.route('/signup')
def signup():
    return "<h2>Signup Page</h2>"


@app.route('/logout')
def logout():
    session.clear()
    flash("You have been successfully logged out.", "success")
    return redirect('/login')


@app.route('/admin')
@login_required(allowed_roles=['admin'])
def admin():
    return render_template("admin.html")


# ✅ ROOM ALLOCATION PAGE
@app.route('/room_allocation')
@login_required(allowed_roles=['admin', 'warden'])
def room_allocation_page():
    return render_template("allocate_room_warden.html")


# ✅ HANDLE ROOM ALLOCATION
@app.route('/allocate_room', methods=['POST'])
@login_required(allowed_roles=['admin', 'warden'])
def allocate_room():
    student_id = request.form['student_id']
    room_id = request.form['room_id']

    cursor = mysql_conn.cursor()

    check_query = """
        SELECT capacity, 
               (SELECT COUNT(*) FROM room_allocation WHERE room_id = %s) as allocated
        FROM room 
        WHERE room_id = %s
    """
    cursor.execute(check_query, (room_id, room_id))
    room_data = cursor.fetchone()

    if not room_data:
        flash("Invalid Room ID: The specified room does not exist.", "error")
        return redirect('/room_allocation')
    
    capacity, allocated = room_data
    if allocated >= capacity:
        flash("Warning: Cannot allocate further! Room capacity has already been reached.", "error")
        return redirect('/room_allocation')

    query = """
        INSERT INTO room_allocation (allocation_date, student_id, room_id)
        VALUES (%s, %s, %s)
    """

    try:
        cursor.execute(query, (date.today(), student_id, room_id))
        mysql_conn.commit()
        flash("Room allocated successfully!", "success")
    except mysql.connector.IntegrityError as err:
        if 'student' in err.msg or 'student_id' in err.msg:
            flash("Invalid Student ID: The specified student does not exist.", "error")
        elif 'room' in err.msg or 'room_id' in err.msg:
            flash("Invalid Room ID: The specified room does not exist.", "error")
        else:
            flash(f"Data Integrity Error: Could not allocate room.", "error")
    except mysql.connector.Error as err:
        flash(f"Database Error: {err.msg}", "error")

    return redirect('/room_allocation')

@app.route('/warden')
@login_required(allowed_roles=['warden'])
def warden_dashboard():
    cursor = mysql_conn.cursor()

    query = """
    SELECT 
        r.room_id,
        r.room_number,
        r.capacity,
        COUNT(ra.student_id) AS allocated_students
    FROM room r
    LEFT JOIN room_allocation ra 
        ON r.room_id = ra.room_id
    GROUP BY r.room_id;
    """

    cursor.execute(query)
    rooms = cursor.fetchall()

    cursor.execute("SELECT hostel_name FROM hostel LIMIT 1")
    hostel_data = cursor.fetchone()
    hostel_name = hostel_data[0] if hostel_data else "Hostel Overview"

    return render_template('warden.html', rooms=rooms, hostel_name=hostel_name)

@app.route('/student_profile/<int:student_id>')
@login_required(allowed_roles=['admin', 'warden'])
def student_profile_by_id(student_id):
    cursor = mysql_conn.cursor(dictionary=True)

    query = """
    SELECT 
        s.student_id,
        s.student_name,
        s.contact_number,
        s.address,
        h.hostel_name,
        h.hostel_type,
        r.room_number,
        r.room_type
    FROM student s
    LEFT JOIN hostel h ON s.hostel_id = h.hostel_id
    LEFT JOIN room_allocation ra 
        ON s.student_id = ra.student_id
        AND ra.allocation_id = (
            SELECT MAX(allocation_id)
            FROM room_allocation
            WHERE student_id = s.student_id
        )
    LEFT JOIN room r ON ra.room_id = r.room_id
    WHERE s.student_id = %s
    """

    cursor.execute(query, (student_id,))
    student = cursor.fetchone()

    return render_template("stud_profile.html", student=student)

@app.route('/student_profile')
@login_required(allowed_roles=['student'])
def my_student_profile():
    student_id = session.get('student_id')
    cursor = mysql_conn.cursor(dictionary=True)

    query = """
    SELECT 
        s.*, d.department_name,
        h.hostel_name, h.hostel_type,
        r.room_number, r.room_type
    FROM student s
    LEFT JOIN department d ON s.department_id = d.department_id
    LEFT JOIN hostel h ON s.hostel_id = h.hostel_id
    LEFT JOIN room_allocation ra ON s.student_id = ra.student_id
    LEFT JOIN room r ON ra.room_id = r.room_id
    WHERE s.student_id = %s
    """

    cursor.execute(query, (student_id,))
    student = cursor.fetchone()

    return render_template("stud_profile.html", student=student)

@app.route('/update_profile', methods=['POST'])
@login_required(allowed_roles=['student'])
def update_profile():
    data = request.get_json()

    student_id = data['student_id']
    phone = data['phone']
    address = data['address']

    cursor = mysql_conn.cursor()
    query = """
    UPDATE student
    SET contact_number=%s, address=%s
    WHERE student_id=%s
    """

    cursor.execute(query, (phone, address, student_id))
    mysql_conn.commit()

    return jsonify({"success": True})

# Add Warden
@app.route('/add_warden', methods=['POST'])
@login_required(allowed_roles=['admin'])
def add_warden():
    name = request.form['warden_name']
    contact = request.form['contact_number']
    joining_date = request.form['joining_date']

    cursor = mysql_conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO warden (warden_name, contact_number, joining_date) VALUES (%s, %s, %s)",
            (name, contact, joining_date)
        )
        mysql_conn.commit()
        flash("Warden added successfully!", "success")
    except mysql.connector.Error as err:
        flash(f"Database Error: {err.msg}", "error")

    return redirect('/wardens')


# View Wardens
@app.route('/wardens')
@login_required(allowed_roles=['admin'])
def wardens():
    cursor = mysql_conn.cursor()
    cursor.execute("SELECT * FROM warden")
    data = cursor.fetchall()
    return render_template('manage_warden.html', wardens=data)


# Delete Warden
@app.route('/delete_warden/<int:id>')
@login_required(allowed_roles=['admin'])
def delete_warden(id):
    cursor = mysql_conn.cursor()
    cursor.execute("DELETE FROM warden WHERE warden_id = %s", (id,))
    mysql_conn.commit()
    return redirect('/wardens')

@app.route('/add_notice', methods=['GET'])
@login_required(allowed_roles=['admin'])
def add_notice_page():
    return render_template("add_notice.html")

@app.route("/add_notice", methods=["POST"])
@login_required(allowed_roles=['admin'])
def add_notice():
    title = request.form["title"]
    content = request.form["content"]
    priority = request.form["priority"]

    notices_collection.insert_one({
        "title": title,
        "content": content,
        "priority": priority,
        "date": datetime.now()
    })

    return render_template("add_notice.html", message="✅ Notice added successfully!")

# ------------------ RUN APP ------------------
if __name__ == '__main__':
    app.run(debug=True)