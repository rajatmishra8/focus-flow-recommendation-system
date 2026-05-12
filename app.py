from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import sqlite3, hashlib, os, json
from datetime import datetime
from textblob import TextBlob

app = Flask(__name__)
app.secret_key = "hca_rec_secret_2024"
DB = "database.db"

# ── DB SETUP ─────────────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS assessments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            stress_level INTEGER,
            focus_loss INTEGER,
            addiction_score INTEGER,
            interest_score INTEGER,
            screen_time REAL,
            problem_text TEXT,
            prediction TEXT,
            recommendation TEXT,
            plan TEXT,
            sentiment REAL,
            keywords TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS feedbacks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            assessment_id INTEGER,
            feedback_text TEXT,
            sentiment REAL,
            keywords TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """)

# ── NLP ───────────────────────────────────────────────────────────────────────
def analyze_problem(text):
    text = text.lower()
    sentiment = TextBlob(text).sentiment.polarity
    keywords = []
    if any(w in text for w in ["stress","pressure","anxiety","overwhelm"]):
        keywords.append("stress")
    if any(w in text for w in ["focus","distract","cannot focus","lost focus","wander"]):
        keywords.append("distraction")
    if any(w in text for w in ["tired","fatigue","exhausted","burnout","sleep"]):
        keywords.append("fatigue")
    if any(w in text for w in ["study","homework","exam","test","assignment","lecture"]):
        keywords.append("study_issue")
    if any(w in text for w in ["phone","social media","instagram","youtube","scroll"]):
        keywords.append("digital_overuse")
    return round(sentiment, 3), keywords

def analyze_feedback(text):
    text = text.lower()
    sentiment = TextBlob(text).sentiment.polarity
    keywords = []
    if any(w in text for w in ["helpful","good","great","amazing","excellent","useful","nice","love","perfect"]):
        keywords.append("positive_feedback")
    if any(w in text for w in ["bad","not helpful","useless","poor","terrible","awful","hate","worst"]):
        keywords.append("negative_feedback")
    if any(w in text for w in ["okay","fine","average","decent","moderate","alright"]):
        keywords.append("neutral_feedback")
    return round(sentiment, 3), keywords

# ── RECOMMENDATION ENGINE ─────────────────────────────────────────────────────
def generate_recommendation(user):
    stress   = user["stress_level"]
    focus    = user["focus_loss"]
    addiction= user["addiction_score"]
    screen   = user["screen_time"]
    interest = user["interest_score"]
    keywords = user.get("keywords", [])

    distraction_load = (focus + addiction) / 2
    cognitive_overload = (stress + focus) / 2
    productivity = 10 / (screen + distraction_load + 1)
    stress_efficiency = interest / (stress + 1)

    # Determine prediction label
    score = (distraction_load + (stress + focus)/2) / 2
    threshold = 3.0
    prediction = "Good Performance" if score < threshold else "Needs Improvement"

    # Primary recommendation
    if "stress" in keywords or stress >= 4:
        rec = "Focus on stress management and mental recovery"
        rec_icon = ""
    elif "distraction" in keywords or focus >= 4:
        rec = "Improve focus and eliminate distractions"
        rec_icon = ""
    elif "digital_overuse" in keywords or addiction >= 4:
        rec = "Reduce digital addiction and screen time"
        rec_icon = ""
    elif "fatigue" in keywords:
        rec = "Prioritize rest, sleep hygiene and energy management"
        rec_icon = ""
    elif productivity < 2:
        rec = "Build a structured study routine and time management system"
        rec_icon = ""
    else:
        rec = "Maintain your balanced academic routine and keep growing"
        rec_icon = ""

    # Detailed plan
    plan = []
    if stress >= 4 or "stress" in keywords:
        plan += [
            {"icon":"","text":"Practice 10–15 mins daily meditation or deep breathing"},
            {"icon":"","text":"Take short mindful breaks between study sessions"},
            {"icon":"","text":"Include a 20-min walk or light exercise daily"}
        ]
    if focus >= 4 or "distraction" in keywords:
        plan += [
            {"icon":"","text":"Use Pomodoro Technique: 25 min study + 5 min break"},
            {"icon":"","text":"Study in a distraction-free, quiet environment"},
            {"icon":"","text":"Write down goals before each study session"}
        ]
    if screen >= 5 or "digital_overuse" in keywords:
        plan += [
            {"icon":"","text":"Limit screen time to 3–4 hours per day"},
            {"icon":"","text":"Disable non-essential notifications while studying"},
            {"icon":"","text":"Use app blockers like Forest or Freedom"}
        ]
    if addiction >= 4:
        plan += [
            {"icon":"","text":"Keep your phone in another room while studying"},
            {"icon":"","text":"Schedule fixed social media slots — not random browsing"}
        ]
    if "fatigue" in keywords:
        plan += [
            {"icon":"","text":"Aim for 7–8 hours of consistent sleep each night"},
            {"icon":"","text":"Stay hydrated and maintain a nutritious diet"}
        ]
    if productivity < 2:
        plan += [
            {"icon":"","text":"Create a weekly study timetable with buffer time"},
            {"icon":"","text":"Break big tasks into smaller, achievable sub-goals"},
            {"icon":"","text":"End each day by reviewing what you accomplished"}
        ]
    if not plan:
        plan = [
            {"icon":"","text":"Continue your current productive habits"},
            {"icon":"","text":"Challenge yourself with slightly harder goals"},
            {"icon":"","text":"Help peers — teaching reinforces your own learning"}
        ]

    explanation = {
        "stress_level": stress,
        "focus_loss": focus,
        "addiction": addiction,
        "screen_time": screen,
        "productivity": round(productivity, 2),
        "stress_efficiency": round(stress_efficiency, 2),
        "keywords": keywords
    }

    return {
        "prediction": prediction,
        "recommendation": rec,
        "rec_icon": rec_icon,
        "plan": plan,
        "explanation": explanation
    }

# ── AUTH ROUTES ───────────────────────────────────────────────────────────────
def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

@app.route("/signup", methods=["GET","POST"])
def signup():
    error = None
    if request.method == "POST":
        username = request.form["username"].strip()
        email    = request.form["email"].strip()
        password = request.form["password"]
        if len(password) < 6:
            error = "Password must be at least 6 characters."
        else:
            try:
                with get_db() as db:
                    db.execute("INSERT INTO users (username, email, password) VALUES (?,?,?)",
                               (username, email, hash_pw(password)))
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                error = "Username or email already exists."
    return render_template("signup.html", error=error)

@app.route("/login", methods=["GET","POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        with get_db() as db:
            user = db.execute("SELECT * FROM users WHERE username=? AND password=?",
                              (username, hash_pw(password))).fetchone()
        if user:
            session["user_id"]   = user["id"]
            session["username"]  = user["username"]
            return redirect(url_for("dashboard"))
        error = "Invalid credentials. Please try again."
    return render_template("login.html", error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ── DASHBOARD ─────────────────────────────────────────────────────────────────
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    with get_db() as db:
        assessments = db.execute(
            "SELECT * FROM assessments WHERE user_id=? ORDER BY created_at DESC LIMIT 5",
            (session["user_id"],)).fetchall()
        feedbacks = db.execute(
            "SELECT * FROM feedbacks WHERE user_id=? ORDER BY created_at DESC LIMIT 3",
            (session["user_id"],)).fetchall()
        total_ass = db.execute("SELECT COUNT(*) as c FROM assessments WHERE user_id=?",
                               (session["user_id"],)).fetchone()["c"]
        total_fb  = db.execute("SELECT COUNT(*) as c FROM feedbacks WHERE user_id=?",
                               (session["user_id"],)).fetchone()["c"]

    avg_sentiment = None
    if feedbacks:
        sentiments = [f["sentiment"] for f in feedbacks if f["sentiment"] is not None]
        if sentiments:
            avg_sentiment = round(sum(sentiments)/len(sentiments), 2)

    return render_template("dashboard.html",
                           assessments=assessments,
                           feedbacks=feedbacks,
                           total_ass=total_ass,
                           total_fb=total_fb,
                           avg_sentiment=avg_sentiment)

# ── ASSESSMENT ────────────────────────────────────────────────────────────────
@app.route("/assess", methods=["GET","POST"])
def assess():
    if "user_id" not in session:
        return redirect(url_for("login"))
    if request.method == "POST":
        data = {
            "stress_level":    int(request.form["stress_level"]),
            "focus_loss":      int(request.form["focus_loss"]),
            "addiction_score": int(request.form["addiction_score"]),
            "interest_score":  int(request.form["interest_score"]),
            "screen_time":     float(request.form["screen_time"]),
            "problem_text":    request.form.get("problem_text","").strip()
        }
        sentiment, keywords = analyze_problem(data["problem_text"]) if data["problem_text"] else (0, [])
        data["keywords"] = keywords

        result = generate_recommendation(data)

        with get_db() as db:
            cur = db.execute("""INSERT INTO assessments
                (user_id,stress_level,focus_loss,addiction_score,interest_score,
                 screen_time,problem_text,prediction,recommendation,plan,sentiment,keywords)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (session["user_id"], data["stress_level"], data["focus_loss"],
                 data["addiction_score"], data["interest_score"], data["screen_time"],
                 data["problem_text"], result["prediction"], result["recommendation"],
                 json.dumps(result["plan"]), sentiment, json.dumps(keywords)))
            ass_id = cur.lastrowid

        return render_template("result.html",
                               result=result,
                               sentiment=sentiment,
                               keywords=keywords,
                               assessment_id=ass_id)
    return render_template("assess.html")

# ── FEEDBACK ──────────────────────────────────────────────────────────────────
@app.route("/feedback", methods=["POST"])
def feedback():
    if "user_id" not in session:
        return jsonify({"error":"Not logged in"}), 401
    text = request.json.get("text","").strip()
    ass_id = request.json.get("assessment_id")
    if not text:
        return jsonify({"error":"Empty feedback"}), 400
    sentiment, keywords = analyze_feedback(text)
    with get_db() as db:
        db.execute("""INSERT INTO feedbacks (user_id, assessment_id, feedback_text, sentiment, keywords)
                      VALUES (?,?,?,?,?)""",
                   (session["user_id"], ass_id, text, sentiment, json.dumps(keywords)))
    label = "Positive " if sentiment > 0.1 else ("Negative " if sentiment < -0.1 else "Neutral ")
    return jsonify({"sentiment": sentiment, "keywords": keywords, "label": label})

# ── STATIC PAGES ──────────────────────────────────────────────────────────────
@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/tools")
def tools():
    return render_template("tools.html")

# ── HISTORY ───────────────────────────────────────────────────────────────────
@app.route("/history")
def history():
    if "user_id" not in session:
        return redirect(url_for("login"))
    with get_db() as db:
        assessments = db.execute(
            "SELECT * FROM assessments WHERE user_id=? ORDER BY created_at DESC",
            (session["user_id"],)).fetchall()
    return render_template("history.html", assessments=assessments)

if __name__ == "__main__":
    init_db()
    app.run(debug=True)