from flask import Flask, render_template, request, redirect, session, url_for,flash,jsonify
from functools import wraps
import mysql.connector
import bcrypt
import random
from datetime import datetime, timedelta
from calendar import monthrange
import calendar  
import os
from dotenv import load_dotenv

load_dotenv()



app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

# -------------------
# DATABASE CONNECTION
# -------------------
db = mysql.connector.connect(
    host=os.getenv("DB_HOST"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME"),
    autocommit=True
)
print("Connected Database:", db.database)
def get_cursor(dictionary=False):
    global db

    try:
        if not db.is_connected():
            db.reconnect(attempts=3, delay=2)
    except:
        db.reconnect(attempts=3, delay=2)

    return db.cursor(dictionary=dictionary, buffered=True)


import requests

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

def generate_ai_content(topic, doubt=None):

    prompt = f"""
The student is weak in the following subjects: {topic}.

Give simple study recommendations for each subject separately.

Format:

Subject Name:
- Tip 1
- Tip 2
- Tip 3

Keep it simple for school students.
"""

    url = "https://api.groq.com/openai/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "openai/gpt-oss-120b",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7
    }

    try:

        response = requests.post(url, headers=headers, json=data)

        print("STATUS CODE:", response.status_code)

        result = response.json()

        print("FULL AI RESPONSE:", result)

        if response.status_code == 200:
            ai_text = result["choices"][0]["message"]["content"]
            return ai_text

        else:
            return "AI API error: " + str(result)

    except Exception as e:

        print("Groq Error:", e)
        return "AI explanation unavailable."
    
#------------------------------------
def calculate_subject_strength(cursor, user_id, practice_id):

    cursor.execute("""
        SELECT 
            subject,
            COUNT(*) AS total,
            IFNULL(SUM(is_correct),0) AS correct
        FROM question_history
        WHERE user_id=%s AND practice_id=%s
        GROUP BY subject
    """,(user_id,practice_id))

    subjects = cursor.fetchall() or []

    strong_subjects = []
    weak_subjects = []

    highest = -1
    lowest = 101

    for sub in subjects:

        total = sub.get("total",0)
        correct = sub.get("correct",0)

        percentage = (correct/total)*100 if total>0 else 0

        if percentage > highest:
            highest = percentage
            strong_subjects = [sub["subject"]]

        elif percentage == highest:
            strong_subjects.append(sub["subject"])

        if percentage < lowest:
            lowest = percentage
            weak_subjects = [sub["subject"]]

        elif percentage == lowest:
            weak_subjects.append(sub["subject"])

    strong_subject = ", ".join(strong_subjects) if strong_subjects else "None"
    weak_subject = ", ".join(weak_subjects) if weak_subjects else "None"

    return strong_subject, weak_subject

# -----------------------------
# Login Decorator
# -----------------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

# -----------------------------
# AI Recommender Route (Updated)
# -----------------------------
@app.route("/ai_recommendation")
@login_required
def ai_recommendation():

    user_id = session["user_id"]
    practice_id = session.get("last_practice_id")
   

    cursor = get_cursor(True)

    # 1️⃣ Weak subject detection (same as before)
    cursor.execute("""
        SELECT subject, COUNT(*) AS total, SUM(is_correct) AS correct
        FROM question_history
        WHERE user_id=%s AND practice_id=%s
        GROUP BY subject
    """, (user_id, practice_id))

    data = cursor.fetchall()
    weak_subjects = []
    lowest = 101

    for row in data:
        total = row["total"]
        correct = row["correct"] or 0
        percentage = (correct / total) * 100 if total > 0 else 0

        if percentage < lowest:
            lowest = percentage
            weak_subjects = [row["subject"]]
        elif percentage == lowest:
            weak_subjects.append(row["subject"])

    weak_subject = ", ".join(weak_subjects) if weak_subjects else "Maths"

    print("Detected weak subject:", weak_subject)

    # 2️⃣ Extract topics from last quiz questions
    cursor.execute("""
        SELECT question
        FROM question_history
        WHERE user_id=%s AND practice_id=%s AND subject=%s
    """, (user_id, practice_id, weak_subject))

    questions = cursor.fetchall()
    topics = []

    for q in questions:
        # Simplified: just take key words from the question
        # (optional: can improve with NLP to detect key concept)
        question_text = q["question"]
        topics.append(question_text)

    topics_str = "; ".join(topics) if topics else weak_subject

    # 3️⃣ Generate AI prompt using only topics
    prompt = f"""
You are a school tutor. The student is weak in {weak_subject}. 
Here are the topics/questions they struggled with: {topics_str}.

Give a **detailed explanation, simple examples, and practical study tips** for each topic. 
Make it easy for a school student to understand. 
Provide 3-5 tips per topic. Use examples if possible.
"""

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "openai/gpt-oss-120b",  # updated working model
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        result = response.json()
        if response.status_code == 200:
            ai_text = result["choices"][0]["message"]["content"]
        else:
            ai_text = "AI API error: " + str(result)
    except Exception as e:
        print("Groq Error:", e)
        ai_text = "AI explanation unavailable."

    return render_template(
        "ai_recommendation.html",
        weak_subject=weak_subject,
        ai_content=ai_text
    )
# -------------------
# HOME ROUTE
# -------------------
@app.route("/")
def home():
    return render_template("index.html")

# -------------------
# LOGIN ROUTE
# -------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    error = None

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        cursor = get_cursor(True)

        cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
        user = cursor.fetchone()

        if not user:
            error = "User not found! Please sign up."

        elif not bcrypt.checkpw(password.encode('utf-8'), user["password"].encode('utf-8')):
            error = "Incorrect password."

        else:
            session["user_id"] = user["id"]
            session["user"] = user["username"]

            cursor.execute(
                "SELECT * FROM user_profile WHERE user_id=%s",
                (user["id"],)
            )

            profile = cursor.fetchone()

            cursor.close()

            if profile:
                return redirect("/dashboard")
            else:
                return redirect("/select")

        cursor.close()

    return render_template("login.html", error=error)

#-------------------------------
#-------Sign up Route ----------
#------------------------------
@app.route("/signup", methods=["GET", "POST"])
def signup():

    if request.method == "POST":
        fullname = request.form["fullname"]
        email = request.form["email"]
        password = request.form["password"]

        username = fullname.lower().replace(" ", "") + str(random.randint(100, 999))
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        cursor = get_cursor()

        cursor.execute(
            "INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
            (username, email, hashed_password.decode('utf-8'))
        )

        cursor.close()

        flash(f"Account created! Your username is: {username}", "success")

        return redirect("/login")

    return render_template("signup.html")


# -------------------

# -------------------
# LOGOUT
@app.route("/logout")
@login_required
def logout():
    session.clear()
    return redirect(url_for("login"))

# -------------------
# SELECT SUBJECT/CLASS
@app.route("/select", methods=["GET", "POST"])
@login_required
def select():
    # cursor = db.cursor()
    cursor = get_cursor()
    
    if request.method == "POST":
        selected_class = request.form["class"]
        
        # Default subject logic (first subject of selected class)
        cursor.execute(
            "SELECT subject_name FROM class_subjects WHERE class_name=%s ORDER BY id LIMIT 1",
            (selected_class,)
        )
        subject_row = cursor.fetchone()
        selected_subject = subject_row[0] if subject_row else "English"  # fallback English
        
        cursor.execute(
            "SELECT id, change_count FROM user_profile WHERE user_id=%s",
            (session["user_id"],)
        )
        profile = cursor.fetchone()

        if profile:
            new_count = profile[1] + 1
            cursor.execute(
                "UPDATE user_profile SET selected_class=%s, selected_subject=%s, change_count=%s WHERE id=%s",
                (selected_class, selected_subject, new_count, profile[0])
            )
        else:
            cursor.execute(
                "INSERT INTO user_profile (user_id, selected_class, selected_subject, change_count) VALUES (%s, %s, %s, %s)",
                (session["user_id"], selected_class, selected_subject, 1)
            )
        # db.commit()
        return redirect("/dashboard")

    # Pre-fill current profile
    cursor.execute(
        "SELECT selected_class FROM user_profile WHERE user_id=%s",
        (session["user_id"],)
    )
    profile = cursor.fetchone()
    selected_class = profile[0] if profile else ""
    
    return render_template("select.html", selected_class=selected_class)

# -------------------
# DASHBOARD
# -------------------
# DASHBOARD
# -------------------
@app.route("/dashboard")
@login_required
def dashboard():
    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]
    # cursor = db.cursor(dictionary=True)
    cursor = get_cursor(True)

    #---------------------------------------------------
    practice_id = session.get("last_practice_id")

    if practice_id:
        strong_subject, weak_subject = calculate_subject_strength(cursor, user_id, practice_id)
    else:
        strong_subject = "None"
        weak_subject = "None"

    # Profile Info
    cursor.execute("SELECT selected_class, change_count FROM user_profile WHERE user_id=%s", (user_id,))
    profile = cursor.fetchone()
    selected_class = profile["selected_class"] if profile else "Not selected"


    # Subjects of that class
    cursor.execute("SELECT subject_name FROM class_subjects WHERE class_name=%s", (selected_class,))
    subjects = [row["subject_name"] for row in cursor.fetchall()]
    selected_subject = subjects[0] if subjects else None  # just for display, dashboard me dropdown nahi

    # Weekly Practice Stats
    # -------------------
    # WEEKLY PRACTICE (From question_history)
    # -------------------

    cursor.execute("""
        SELECT subject,
            COUNT(*) as total_sessions,
            AVG(score) as avg_score
        FROM practice_history
        WHERE user_id=%s
        AND created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
        GROUP BY subject
    """, (user_id,))

    weekly_data = cursor.fetchall()

    # Weekly Sessions (days practiced)
    cursor.execute("""
        SELECT COUNT(DISTINCT DATE(created_at)) AS sessions
        FROM question_history
        WHERE user_id=%s
        AND created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
    """, (user_id,))
    weekly_sessions = cursor.fetchone()["sessions"] or 0

    # Most Practiced
    if weekly_data:
        most_practiced = max(
            weekly_data,
            key=lambda x: x["total_sessions"]
        )["subject"]
    else:
        most_practiced = "None"

    # Weekly Graph Data
    cursor.execute("""
        SELECT DATE(created_at) AS date, subject, score
        FROM practice_history
        WHERE user_id=%s
        AND created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
        ORDER BY created_at
    """, (user_id,))
    graph_data = cursor.fetchall()
    dates = [str(row["date"]) for row in graph_data]
    scores = [float(row["score"]) for row in graph_data]
    subjects_graph = [row["subject"] for row in graph_data]

    # Practice History
    cursor.execute("""
        SELECT created_at, subject, score, questions_attempted, correct_answers
        FROM practice_history
        WHERE user_id=%s
        ORDER BY created_at DESC
    """, (user_id,))
    history_data = cursor.fetchall()
    total_sessions = sum([row["total_sessions"] for row in weekly_data])

    avg_score = round(
        sum([row["avg_score"] * row["total_sessions"] for row in weekly_data]) / total_sessions,
        2
    ) if total_sessions else 0

    return render_template(
    "dashboard.html",
    full_name=session["user"],
    username=session["user"],
    selected_class=selected_class,
    subjects=subjects,
    selected_subject=selected_subject,

    weekly_sessions=weekly_sessions,
    avg_score=avg_score,
    most_practiced=most_practiced,

    strong_subject=strong_subject,
    weak_subject=weak_subject,

    # strong_subject=strong_subject_str,
    # weak_subject=weak_subject_str,

    dates=dates,
    scores=scores,
    subjects_graph=subjects_graph,
    history_data=history_data
)


# -------------------
# # PRACTICE SESSION (Mixed MCQs)
# -------------------
# -------------------
# PRACTICE SESSION (AI + Guaranteed 10 Questions)
# -------------------
import requests
import json

@app.route("/practice")
@login_required
def practice():

    session.pop("last_practice_id", None)   # 🔥 OLD ANALYSIS CLEAR

    user_id = session["user_id"]
    # cursor = db.cursor(dictionary=True)
    cursor = get_cursor(True)

    # Total practice attempts
    cursor.execute(
        "SELECT COUNT(*) AS total FROM practice_history WHERE user_id=%s",
        (user_id,)
    )

    total_attempts = cursor.fetchone()["total"]

    questions = []

    # -------------------
    # FIRST TIME USER
    # -------------------
    if total_attempts == 0:
        cursor.execute("""
            SELECT q.id, q.subject, q.question, q.option1, q.option2, q.option3, q.option4, q.correct_answer
            FROM questions q
            JOIN class_subjects cs ON q.subject = cs.subject_name
            JOIN user_profile up ON up.selected_class = cs.class_name
            WHERE up.user_id=%s
            ORDER BY RAND() LIMIT 10
        """, (user_id,))
        questions = cursor.fetchall()

    # -------------------
    # RETURNING USER
    # -------------------
    else:
        # Weak subject detection
        cursor.execute("""
            SELECT subject, AVG(score) AS avg_score
            FROM practice_history
            WHERE user_id=%s
            GROUP BY subject
            ORDER BY AVG(score) ASC
            LIMIT 1
        """, (user_id,))
        weak = cursor.fetchone()
        weak_subject = weak["subject"] if weak else None

        ai_questions = []

        # -------------------
        # AI QUESTION GENERATION
        # -------------------
        if weak_subject:
            prompt = f"""
            Generate 5 multiple choice questions for class 6-8 subject {weak_subject}.

            Return ONLY valid JSON.

            Example:

            [
            {{
            "subject":"{weak_subject}",
            "question":"What is 5 + 3?",
            "option1":"6",
            "option2":"8",
            "option3":"10",
            "option4":"7",
            "correct_answer":"option2"
            }}
            ]
            """

            try:
                response = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {GROQ_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "openai/gpt-oss-120b",
                        "messages": [
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        "temperature": 0.7
                    }
                )

                data = response.json()

                text_output = data["choices"][0]["message"]["content"]

                try:
                    ai_questions = json.loads(text_output)
                except:
                    ai_questions = []


            except Exception as e:
                print("AI ERROR:", e)
                ai_questions = []

        print("AI Questions Count:", len(ai_questions))

        # -------------------
        # ADD AI QUESTIONS (max 5)
        # -------------------
        if ai_questions and isinstance(ai_questions, list):
            questions.extend(ai_questions[:5])

        # -------------------
        # FILL REMAINING FROM DB
        # -------------------
        remaining = 10 - len(questions)

        if remaining > 0:
            cursor.execute("""
                SELECT q.id, q.subject, q.question, q.option1, q.option2, q.option3, q.option4, q.correct_answer
                FROM questions q
                JOIN class_subjects cs ON q.subject = cs.subject_name
                JOIN user_profile up ON up.selected_class = cs.class_name
                WHERE up.user_id=%s
                ORDER BY RAND() LIMIT %s
            """, (user_id, remaining))

            db_fill = cursor.fetchall()
            questions.extend(db_fill)

        print("Final Question Count:", len(questions))

    quiz_subject = questions[0]["subject"] if questions else None
    
    cursor.close()

    return render_template("quiz.html", questions=questions, subject=quiz_subject)


@app.route("/submit_quiz", methods=["POST"])
@login_required
def submit_quiz():

    user_id = session["user_id"]
    total_questions = int(request.form["total_questions"])

    correct = 0
    wrong = 0
    subject_set = set()

    # cursor = db.cursor(dictionary=True)
    cursor = get_cursor(True)

    questions_data = []

    practice_id = random.randint(100000,999999)
    session["last_practice_id"] = practice_id

    for i in range(total_questions):

        question_id = request.form.get(f"question_id{i}")
        selected = request.form.get(f"q{i}")

        cursor.execute(
            "SELECT subject, question, correct_answer FROM questions WHERE id=%s",
            (question_id,)
        )

        q = cursor.fetchone()

        if not q:
            continue

        subject_set.add(q["subject"])

        correct_answer = q["correct_answer"]
        is_correct = 1 if selected == correct_answer else 0

        if is_correct:
            correct += 1
        else:
            wrong += 1

        questions_data.append({
            "subject": q["subject"],
            "question": q["question"],
            "selected": selected,
            "correct": correct_answer,
            "is_correct": is_correct
        })

    score = round((correct / total_questions) * 100, 2)

    subject = list(subject_set)[0] if subject_set else "General"

    # ------------------------
    # INSERT PRACTICE FIRST
    # ------------------------

    # ------------------------

    for q in questions_data:
        cursor.execute("""
            INSERT INTO quiz_analysis
            (user_id, subject, correct, total, accuracy)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            user_id,
            q["subject"],
            q["is_correct"],
            1,  # each question counts as 1
            q["is_correct"] * 100  # 1 correct = 100%, 0 = 0%
        ))

    db.commit()

    cursor.execute("""
        INSERT INTO practice_history
        (user_id, subject, questions_attempted, correct_answers, score)
        VALUES (%s, %s, %s, %s, %s)
    """, (
        user_id,
        subject,
        total_questions,
        correct,
        score
    ))

    # db.commit()

    practice_id = cursor.lastrowid
   
    

    # ------------------------
    # INSERT QUESTIONS
    # ------------------------

    for q in questions_data:

        cursor.execute("""
        INSERT INTO question_history
        (user_id, practice_id, subject, question,
        selected_option, correct_option, is_correct)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (
            user_id,
            practice_id,
            q["subject"],
            q["question"],
            q["selected"],
            q["correct"],
            q["is_correct"]
        ))

    # db.commit()

    session["last_practice_id"] = practice_id

    return redirect(url_for("analysis"))
# -------------------
# WEEKLY PROGRESS

# WEEKLY / MONTHLY PROGRESS
@app.route("/weekly_progress")
def weekly_progress():

    

    user_id = session["user_id"]
    # cursor = db.cursor(dictionary=True)
    cursor = get_cursor(True)

    now = datetime.now()
    year = now.year
    month = now.month
    today = now.day

    month_name = now.strftime("%B")

    # Total days in current month
    total_days_in_month = calendar.monthrange(year, month)[1]

    # Only count days till today (future days excluded)
    total_days = today

    # Get distinct practice days of current month
    cursor.execute("""
        SELECT DISTINCT DATE(created_at) as date
        FROM practice_history
        WHERE user_id=%s
        AND MONTH(created_at)=%s
        AND YEAR(created_at)=%s
    """, (user_id, month, year))

    practice_data = cursor.fetchall()
    present_days = [row["date"].day for row in practice_data]

    present_count = len(set(present_days))
    inactive_count = total_days - present_count

    

    # Monthly quiz attempts
    cursor.execute("""
        SELECT COUNT(*) as quiz_count
        FROM practice_history
        WHERE user_id=%s
        AND MONTH(created_at)=%s
        AND YEAR(created_at)=%s
    """, (user_id, month, year))

    quiz_count = cursor.fetchone()["quiz_count"]

    # Total attempts overall
    cursor.execute("""
        SELECT COUNT(*) as total_attempts
        FROM practice_history
        WHERE user_id=%s
    """, (user_id,))

    total_attempts = cursor.fetchone()["total_attempts"]

    # Average attempts per active day
    if present_count > 0:
        avg_attempts_per_day = round(quiz_count / present_count, 1)
    else:
        avg_attempts_per_day = 0

    # Attendance percentage
    if total_days > 0:
        attendance_percentage = round((present_count / total_days) * 100, 1)
    else:
        attendance_percentage = 0

    # Circle calculation
    radius = 70
    circumference = 2 * 3.1416 * radius

    dash_offset = round(circumference - (circumference * attendance_percentage / 100), 2)

    cursor.close()

    return render_template(
        "weekly_progress.html",
        month_name=month_name,
        year=year,
        total_days=total_days,
        total_days_in_month=total_days_in_month,
        present_days=present_days,
        present_count=present_count,
        inactive_count=inactive_count,
        attendance_percentage=attendance_percentage,
        quiz_count=quiz_count,
        total_attempts=total_attempts,
        avg_attempts_per_day=avg_attempts_per_day,
        dash_offset=dash_offset,
        circumference=circumference
    )
# -------------------
# -------------------
# # VIEW ANALYSIS (Professional Version)
# -------------------
# VIEW ANALYSIS (Professional Version + AI Notes)
# -------------------
@app.route("/analysis")
@login_required
def analysis():
    practice_id = session.get("last_practice_id")
    user_id = session.get("user_id")

    if not user_id:
        return redirect(url_for("login"))

    # cursor = db.cursor(dictionary=True)
    cursor = get_cursor(True)

    # --------------------------------
    # 1️⃣ Overall Stats
    # --------------------------------
    practice_id = session.get("last_practice_id")

    cursor.execute("""
    SELECT 
    COUNT(*) as total_attempts,
    SUM(is_correct) as correct_answers
    FROM question_history
    WHERE user_id=%s AND practice_id=%s
    """,(user_id,practice_id))

    result = cursor.fetchone()

    stats = {
        "total_attempts": 0,
        "avg_score": 0
    }

    if result:

        total = result["total_attempts"] or 0
        correct = result["correct_answers"] or 0

        stats["total_attempts"] = total

        if total > 0:
            stats["avg_score"] = round((correct/total)*100,2)

    # --------------------------------
# 2️⃣ Subject-wise Performance (last practice only)
# --------------------------------
    practice_id = session.get("last_practice_id")

    cursor.execute("""
        SELECT 
            subject,
            COUNT(*) AS total,
            IFNULL(SUM(is_correct), 0) AS correct
        FROM question_history
        WHERE user_id = %s AND practice_id = %s
        GROUP BY subject
    """, (user_id, practice_id))

    subjects = cursor.fetchall() or []

    strong_subjects = []
    weak_subjects = []

    highest = -1
    lowest = 101

    for sub in subjects:
        total = sub.get("total", 0)
        correct = sub.get("correct", 0)
        percentage = (correct / total) * 100 if total > 0 else 0
        sub["percentage"] = round(percentage, 2)

        # Strong subjects
        if percentage > highest:
            highest = percentage
            strong_subjects = [sub["subject"]]
        elif percentage == highest:
            strong_subjects.append(sub["subject"])

        # Weak subjects
        if percentage < lowest:
            lowest = percentage
            weak_subjects = [sub["subject"]]
        elif percentage == lowest:
            weak_subjects.append(sub["subject"])

    

    # --------------------------------
    # 3️⃣ Question Breakdown
    practice_id = session.get("last_practice_id")

    cursor.execute("""
        SELECT question, subject, is_correct
        FROM question_history
        WHERE user_id = %s AND practice_id = %s
        ORDER BY created_at DESC
    """, (user_id, practice_id))

    questions = cursor.fetchall() or []

    # --------------------------------
    # 4️⃣ Render Template
    # --------------------------------
    return render_template(
        "analysis.html",
        stats=stats,
        avg_score=stats["avg_score"],  # 👈 ye add karo
        subjects=subjects,
        questions=questions,
        strong_subjects=strong_subjects,
        weak_subjects=weak_subjects,
        ai_content=""   # optional AI notes
    )

@app.route("/delete_account", methods=["POST"])
@login_required
def delete_account():
    user_id = session["user_id"]
    # cursor = db.cursor()
    cursor = get_cursor()

    try:
        # 1. Delete from dependent tables first (foreign keys)
        cursor.execute("DELETE FROM question_history WHERE user_id=%s", (user_id,))
        cursor.execute("DELETE FROM practice_history WHERE user_id=%s", (user_id,))
        cursor.execute("DELETE FROM user_profile WHERE user_id=%s", (user_id,))
        # 2. Delete user
        cursor.execute("DELETE FROM users WHERE id=%s", (user_id,))
        # db.commit()

        # Clear session
        session.clear()
        return redirect(url_for("login"))

    except Exception as e:
        db.rollback()
        return f"Error deleting account: {str(e)}"
    

# -------------------
# RUN APP
# -------------------
if __name__ == "__main__":
    app.run(debug=True)