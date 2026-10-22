from flask import Flask, render_template, request, redirect, session, flash, jsonify
import pandas as pd
import sqlite3
import re
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

from model.gap_analyzer import analyze_gap
from model.strategy_chat import generate_strategy_reply
from model.skill_test import evaluate_skill_test, generate_skill_test, normalize_skill_name

app = Flask(__name__)
app.secret_key = "secret123"


def parse_skills_text(raw_text):
    if not raw_text:
        return []

    cleaned = raw_text.replace("\r", "\n").strip()
    if not cleaned:
        return []

    if "," in cleaned or "\n" in cleaned:
        parts = re.split(r"[\n,]+", cleaned)
    else:
        parts = cleaned.split()

    seen = set()
    skills = []
    for part in parts:
        skill = part.strip()
        lowered = skill.lower()
        if skill and lowered not in seen:
            seen.add(lowered)
            skills.append(skill)

    return skills


def parse_role_skills(raw_text):
    if not raw_text:
        return []

    return [part for part in re.split(r"[\s,]+", str(raw_text).strip()) if part]


def load_roles():
    df = pd.read_csv("dataset/skills.csv")
    df.columns = df.columns.str.strip().str.lower()
    return list(dict.fromkeys(df["role"].dropna().astype(str).str.strip().tolist()))


def build_chart_labels(required_skills, known_skills):
    labels = []
    seen = set()

    for skill in list(required_skills) + list(known_skills):
        key = normalize_skill_name(skill)
        if key and key not in seen:
            seen.add(key)
            labels.append(skill)

    return labels


def get_user_details(username):
    conn = sqlite3.connect("users.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        "SELECT username, email, phone, age, college, degree, year FROM users WHERE username=?",
        (username,)
    )
    user = cur.fetchone()
    conn.close()
    return dict(user) if user else None

# -------------------------
# DATABASE INIT
# -------------------------
def init_db():
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        email TEXT,
        phone TEXT,
        age INTEGER,
        college TEXT,
        degree TEXT,
        year TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

# -------------------------
# LOGIN REQUIRED (FIXED)
# -------------------------
def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            print("NOT LOGGED IN")  # DEBUG
            return redirect("/login")
        return func(*args, **kwargs)
    return wrapper

# -------------------------
# REGISTER
# -------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        try:
            username = request.form["username"].strip().lower()
            password = request.form["password"].strip()
            email = request.form["email"].strip()
            phone = request.form["phone"].strip()
            age = request.form["age"]
            college = request.form["college"].strip()
            degree = request.form["degree"].strip()
            year = request.form["year"].strip()

            # VALIDATION
            if len(username) < 3:
                flash("Username must be at least 3 characters", "error")
                return redirect("/register")

            if not re.match(r"^(?=.*[0-9])(?=.*[!@#$%^&*]).{6,}$", password):
                flash("Weak password", "error")
                return redirect("/register")

            if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
                flash("Invalid email", "error")
                return redirect("/register")

            if not re.match(r"^\d{10}$", phone):
                flash("Invalid phone", "error")
                return redirect("/register")

            if not age.isdigit() or int(age) < 16 or int(age) > 100:
                flash("Invalid age", "error")
                return redirect("/register")

            hashed_password = generate_password_hash(password)

            conn = sqlite3.connect("users.db")
            cur = conn.cursor()

            cur.execute("""
            INSERT INTO users 
            (username, password, email, phone, age, college, degree, year)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (username, hashed_password, email, phone, age, college, degree, year))

            conn.commit()
            conn.close()

            # AUTO LOGIN
            session["user"] = username
            print("REGISTER SUCCESS:", username)  # DEBUG

            flash("Registered successfully!", "success")
            return redirect("/")

        except Exception as e:
            print("REGISTER ERROR:", e)
            flash("Error: " + str(e), "error")
            return redirect("/register")

    return render_template("register.html")

# -------------------------
# LOGIN
# -------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    print("LOGIN PAGE HIT")  # DEBUG

    if "user" in session:
        print("Already logged in:", session["user"])
        return redirect("/")

    if request.method == "POST":
        username = request.form["username"].strip().lower()
        password = request.form["password"].strip()

        print("LOGIN TRY:", username)  # DEBUG

        conn = sqlite3.connect("users.db")
        cur = conn.cursor()

        cur.execute("SELECT * FROM users WHERE username=?", (username,))
        user = cur.fetchone()

        conn.close()

        print("DB RESULT:", user)  # DEBUG

        if user and check_password_hash(user[2], password):
            session["user"] = username
            print("LOGIN SUCCESS")  # DEBUG
            flash("Login successful!", "success")
            return redirect("/")
        else:
            print("LOGIN FAILED")  # DEBUG
            flash("Invalid username or password", "error")
            return redirect("/login")

    return render_template("login.html")

# -------------------------
# LOGOUT
# -------------------------
@app.route("/logout")
def logout():
    session.pop("user", None)
    flash("Logged out successfully", "success")
    return redirect("/login")

# -------------------------
# HOME
# -------------------------
@app.route("/")
@login_required
def home():
    print("HOME LOADED FOR:", session.get("user"))  # DEBUG

    try:
        roles = load_roles()
        strategy_starters = [
            "I want a 6-week roadmap for this role.",
            "Which skills should I learn first to close the gap?",
            "Suggest a portfolio project I can build next.",
            "How should I prepare for interviews in this path?",
        ]

        return render_template(
            "index.html",
            roles=roles,
            featured_roles=roles[:8],
            strategy_starters=strategy_starters,
            user=session["user"],
            active_page="dashboard",
            page_eyebrow="Career Strategy Workspace",
            page_title="Plan your next move with clarity",
            page_description="Track your role fit, pressure-test your skills, and talk through a practical learning strategy in one place.",
        )

    except Exception as e:
        print("HOME ERROR:", e)
        return "Error loading dashboard"

# -------------------------
# ANALYZE
# -------------------------
@app.route("/analyze", methods=["POST"])
@login_required
def analyze():
    try:
        user_skills = request.form["skills"]
        selected_role = request.form["role"]
        session["last_skills_input"] = user_skills

        match, missing, matched = analyze_gap(user_skills, selected_role)
        known_skills = parse_skills_text(user_skills)
        chart_labels = build_chart_labels(matched + missing, known_skills)

        return render_template(
            "result.html",
            match=match,
            missing=missing,
            matched=matched,
            role=selected_role,
            known_skills=known_skills,
            chart_labels=chart_labels,
            user=session["user"],
            active_page="dashboard",
            page_eyebrow="Role Fit Snapshot",
            page_title="Your current gap analysis",
            page_description="See how your listed skills compare with the target role before you move into deeper assessment.",
        )

    except Exception as e:
        print("ANALYZE ERROR:", e)
        flash("Error analyzing skills", "error")
        return redirect("/")


@app.route("/strategy_chat", methods=["POST"])
@login_required
def strategy_chat():
    payload = request.get_json(silent=True) or {}
    message = str(payload.get("message", "")).strip()
    selected_role = str(payload.get("role", "")).strip()
    raw_skills = payload.get("skills", "")
    history = session.get("strategy_chat_history", [])
    context_signature = {
        "role": selected_role.lower(),
        "skills": [skill.lower() for skill in parse_skills_text(str(raw_skills or ""))],
    }
    previous_context = session.get("strategy_chat_context")

    if not message:
        return jsonify({"error": "Please enter a question for the strategy coach."}), 400

    if previous_context != context_signature:
        history = []

    response = generate_strategy_reply(
        message=message,
        selected_role=selected_role,
        raw_skills=raw_skills,
        recent_messages=history[-6:],
    )

    history.append({"role": "user", "content": message[:240]})
    history.append({"role": "assistant", "content": response.get("reply", "")[:240]})
    session["strategy_chat_history"] = history[-8:]
    session["strategy_chat_context"] = context_signature

    return jsonify(response)


@app.route("/profile")
@login_required
def profile():
    user_details = get_user_details(session["user"])
    if not user_details:
        flash("User profile not found", "error")
        return redirect("/")

    return render_template(
        "profile.html",
        user=session["user"],
        profile=user_details,
        active_page="profile",
        page_eyebrow="Account Snapshot",
        page_title="Your learner profile",
        page_description="Keep your academic and contact details in one place so the rest of the workspace stays personalized.",
    )

# -------------------------
# RATE SKILLS
# -------------------------
@app.route("/rate_skills", methods=["GET", "POST"])
@login_required
def rate_skills_form():
    roles = load_roles()

    if request.method == "POST":
        raw_skills = request.form.get("skills", "")
        selected_role = request.form.get("role", "")
    else:
        raw_skills = request.args.get("skills") or session.get("last_skills_input", "")
        selected_role = request.args.get("role") or session.get("last_selected_role", "")

    skills_list = parse_skills_text(raw_skills)
    questions_by_skill = generate_skill_test(skills_list) if skills_list else {}

    if raw_skills:
        session["last_skills_input"] = raw_skills
    if selected_role:
        session["last_selected_role"] = selected_role

    if not selected_role and roles:
        selected_role = roles[0]

    return render_template(
        "rate_skills.html",
        skills=skills_list,
        questions_by_skill=questions_by_skill,
        skills_input=raw_skills,
        roles=roles,
        selected_role=selected_role,
        user=session["user"],
        active_page="skill_test",
        page_eyebrow="Capability Benchmark",
        page_title="Run a practical skill check",
        page_description="Generate short coding prompts for your current stack, then convert the results into a clearer upskilling plan.",
    )


@app.route("/submit_ratings", methods=["POST"])
@login_required
def submit_ratings():
    try:
        raw_skills = request.form.get("skills_input", "")
        skills_list = parse_skills_text(raw_skills)
        selected_role = request.form.get("target_role", "").strip() or session.get("last_selected_role", "")
        results = evaluate_skill_test(skills_list, request.form)
        normalized_ratings = results["ratings"]

        skills_df = pd.read_csv("dataset/skills.csv")
        skills_df.columns = skills_df.columns.str.strip().str.lower()

        if not selected_role:
            flash("Please select a target role", "error")
            return redirect("/rate_skills")

        suggested_role = selected_role
        matched_skills = []
        missing_skills = []
        weak_skills = []
        suggested_role_row = skills_df[skills_df["role"].str.strip().str.lower() == selected_role.strip().lower()]
        if not suggested_role_row.empty:
            suggested_role_skills = parse_role_skills(suggested_role_row.iloc[0]["skills"])
            compact_ratings = {
                normalize_skill_name(skill): {"name": skill, "rating": rating}
                for skill, rating in normalized_ratings.items()
            }

            for role_skill in suggested_role_skills:
                role_key = normalize_skill_name(role_skill)
                if role_key in compact_ratings:
                    matched_skills.append(role_skill)
                    if compact_ratings[role_key]["rating"] <= 2:
                        weak_skills.append({
                            "skill": role_skill,
                            "rating": compact_ratings[role_key]["rating"]
                        })
                else:
                    missing_skills.append(role_skill)
        else:
            flash("Selected role was not found", "error")
            return redirect("/rate_skills")

        role_match = round((len(matched_skills) / len(suggested_role_skills)) * 100) if suggested_role_skills else 0

        courses_df = pd.read_csv("dataset/courses.csv")
        courses_df.columns = courses_df.columns.str.strip().str.lower()

        role_column = "role" if "role" in courses_df.columns else "pythorole"
        courses = courses_df[courses_df[role_column].str.strip().str.lower() == suggested_role.strip().lower()]
        course_records = courses[["course", "platform"]].rename(
            columns={"course": "Course", "platform": "Platform"}
        ).to_dict(orient="records")

        low_skills = [item["skill"] for item in weak_skills[:3]]
        if not low_skills:
            sorted_skills = sorted(results["skill_results"], key=lambda item: (item["rating"], item["average_score"]))
            low_skills = [item["skill"] for item in sorted_skills[:3]] or list(normalized_ratings.keys())

        timetable = {
            "Monday": [f"Practice {low_skills[0]}"] if len(low_skills) > 0 else ["Review skills"],
            "Wednesday": [f"Learn {low_skills[1]}"] if len(low_skills) > 1 else ["Continue course work"],
            "Friday": [f"Build mini task in {low_skills[2]}"] if len(low_skills) > 2 else ["Work on a mini project"],
            "Sunday": ["Revise concepts", "Complete one lesson"],
        }

        return render_template(
            "ratings_result.html",
            ratings=normalized_ratings,
            skill_results=results["skill_results"],
            overall_score=results["overall_score"],
            answered_questions=results["answered_questions"],
            total_questions=results["total_questions"],
            target_role=selected_role,
            role_match=role_match,
            suggested_role=suggested_role,
            suggested_role_skills=suggested_role_skills,
            matched_skills=matched_skills,
            missing_skills=missing_skills,
            weak_skills=weak_skills,
            courses=course_records,
            timetable=timetable,
            user=session["user"],
            active_page="skill_test",
            page_eyebrow="Assessment Insights",
            page_title="Your skill test report",
            page_description="Review strengths, weak spots, and the fastest next actions for your target role.",
        )

    except Exception as e:
        print("SUBMIT RATINGS ERROR:", e)
        flash("Error processing skill ratings", "error")
        return redirect("/rate_skills")

# -------------------------
# RUN
# -------------------------
if __name__ == "__main__":
    app.run(debug=True)
