import re


QUESTION_LIBRARY = {
    "python": [
        ("Function Logic", "Write code for a `{skill}` function that filters input data and returns a sorted result.", ["def", "return", "if", "for"]),
        ("Data Processing", "Write `{skill}` code that groups records by a key and prints a summary.", ["for", "dict", "print", "return"]),
        ("Validation Task", "Write `{skill}` code that validates input, handles errors, and returns a clean output.", ["if", "return", "error", "try"]),
    ],
    "sql": [
        ("Aggregation Query", "Write an SQL query that returns the top 5 rows by total amount grouped by customer.", ["select", "sum", "from", "group by", "order by"]),
        ("Join Query", "Write an SQL query joining two tables and returning the latest record for each user.", ["select", "join", "max", "group by", "from"]),
        ("Filter Query", "Write an SQL query that finds rows missing activity in the last 30 days.", ["select", "where", "from", "null"]),
    ],
    "frontend": [
        ("UI Layout", "Write code for a `{skill}` task that builds a responsive card or dashboard layout.", ["class", "return", "div", "display"]),
        ("Interactive Form", "Write code for a `{skill}` form with validation and clear error handling.", ["input", "button", "if", "error"]),
        ("State Update", "Write code for a `{skill}` feature that loads data and renders a list.", ["map", "fetch", "return", "state"]),
    ],
    "backend": [
        ("API Route", "Write `{skill}` code for an API endpoint that returns JSON for a single resource.", ["route", "return", "json", "def"]),
        ("Create Handler", "Write `{skill}` code that accepts input, validates it, and stores a record.", ["post", "if", "insert", "return"]),
        ("Auth Check", "Write `{skill}` logic that checks a token before serving a request.", ["token", "if", "return", "request"]),
    ],
    "data": [
        ("Formula Or Script", "Write code or formula logic for a `{skill}` task that looks up a value from a table.", ["lookup", "if", "return", "value"]),
        ("Summary Report", "Write code or formula logic for a `{skill}` task that totals values by category.", ["sum", "group", "category", "total"]),
        ("Status Rule", "Write code or formula logic for a `{skill}` task that labels rows as High, Medium, or Low.", ["if", "high", "medium", "low"]),
    ],
    "ml": [
        ("Model Pipeline", "Write `{skill}` code that splits data, trains a model, and prints an evaluation score.", ["fit", "predict", "score", "print"]),
        ("Preprocessing", "Write `{skill}` code that cleans or scales data before training.", ["transform", "fit", "data", "return"]),
        ("Inference Step", "Write `{skill}` code that loads a model and returns predictions for new input.", ["load", "predict", "return", "model"]),
    ],
    "devops": [
        ("Config File", "Write `{skill}` code, YAML, or commands to deploy an app service.", ["deploy", "image", "service", "port"]),
        ("Automation", "Write `{skill}` pipeline logic that installs dependencies and runs tests.", ["test", "build", "run", "pipeline"]),
        ("Ops Debugging", "Write `{skill}` commands or script logic to inspect logs and fix a failed process.", ["log", "status", "restart", "error"]),
    ],
    "mobile": [
        ("Screen UI", "Write `{skill}` code for a screen with a title, button, and list.", ["class", "build", "return", "button"]),
        ("API Loading", "Write `{skill}` code that fetches data from an API and shows loading state.", ["async", "await", "return", "loading"]),
        ("Navigation", "Write `{skill}` code that moves from one screen to another and passes data.", ["intent", "navigate", "route", "return"]),
    ],
    "security": [
        ("Input Safety", "Write `{skill}` code that validates and sanitizes user input.", ["if", "validate", "sanitize", "return"]),
        ("Credential Protection", "Write `{skill}` code that stores passwords or secrets safely.", ["hash", "salt", "secret", "return"]),
        ("Access Control", "Write `{skill}` logic for rate limiting or token verification.", ["token", "limit", "if", "return"]),
    ],
    "generic": [
        ("Core Task", "Write code for a practical `{skill}` task with inputs, processing, and returned output.", ["function", "input", "return"]),
        ("Validation Task", "Write code or pseudocode for a `{skill}` flow with validation and error handling.", ["if", "error", "return"]),
        ("Mini Feature", "Write code or pseudocode for a small `{skill}` feature that stores output and prints a summary.", ["store", "print", "return"]),
    ],
}

SKILL_CATEGORIES = {
    "python": "python", "java": "python", "dsa": "python", "oops": "python",
    "sql": "sql",
    "html": "frontend", "css": "frontend", "javascript": "frontend", "react": "frontend", "tailwind": "frontend",
    "flask": "backend", "django": "backend", "apis": "backend", "nodejs": "backend",
    "excel": "data", "powerbi": "data", "statistics": "data",
    "machinelearning": "ml", "deeplearning": "ml", "nlp": "ml", "tensorflow": "ml", "pytorch": "ml", "mlops": "ml", "computervision": "ml",
    "aws": "devops", "docker": "devops", "kubernetes": "devops", "cicd": "devops", "linux": "devops", "azure": "devops", "gcp": "devops", "git": "devops",
    "flutter": "mobile", "kotlin": "mobile", "android": "mobile", "firebase": "mobile",
    "networking": "security", "ethicalhacking": "security", "cryptography": "security", "communication": "security",
}

CODE_SIGNALS = ["def ", "return", "for ", "if ", "select ", "from ", "class ", "function", "import ", "{", "}", "(", ")", "json", "api", "deploy", "model"]


def normalize_skill_name(skill):
    return re.sub(r"[^a-z0-9]+", "", str(skill).strip().lower())


def resolve_category(skill):
    return SKILL_CATEGORIES.get(normalize_skill_name(skill), "generic")


def build_questions_for_skill(skill):
    questions = []
    for index, (title, prompt, keywords) in enumerate(QUESTION_LIBRARY[resolve_category(skill)], start=1):
        questions.append({
            "id": f"{normalize_skill_name(skill)}_{index}",
            "skill": skill,
            "index": index,
            "title": title,
            "prompt": prompt.format(skill=skill),
            "expected_keywords": keywords,
        })
    return questions


def generate_skill_test(skills):
    return {skill: build_questions_for_skill(skill) for skill in skills}


def score_to_rating(score):
    if score < 20:
        return 1
    if score < 40:
        return 2
    if score < 60:
        return 3
    if score < 80:
        return 4
    return 5


def rating_label(rating):
    return {1: "Beginner", 2: "Basic", 3: "Working", 4: "Strong", 5: "Advanced"}.get(rating, "Unknown")


def score_answer(answer, expected_keywords):
    text = str(answer or "").strip()
    if not text:
        return {"score": 0, "matched_keywords": [], "missing_keywords": expected_keywords, "answered": False}

    lowered = text.lower()
    matched = [keyword for keyword in expected_keywords if keyword.lower() in lowered]
    missing = [keyword for keyword in expected_keywords if keyword not in matched]
    keyword_score = (len(matched) / max(len(expected_keywords), 1)) * 70
    signal_score = min(sum(1 for signal in CODE_SIGNALS if signal in lowered) * 4, 20)
    structure_score = 10 if len(text.splitlines()) >= 4 or len(text) > 140 else 5
    return {
        "score": round(min(100, keyword_score + signal_score + structure_score)),
        "matched_keywords": matched,
        "missing_keywords": missing,
        "answered": True,
    }


def evaluate_skill_test(skills, form_data):
    ratings = {}
    skill_results = []
    total_questions = 0
    answered_questions = 0
    total_score = 0

    for skill, questions in generate_skill_test(skills).items():
        question_results = []
        skill_total = 0
        missing_concepts = []

        for question in questions:
            total_questions += 1
            answer = form_data.get(f"answer__{question['id']}", "")
            result = score_answer(answer, question["expected_keywords"])
            if result["answered"]:
                answered_questions += 1
            skill_total += result["score"]
            total_score += result["score"]
            missing_concepts.extend(result["missing_keywords"])
            question_results.append({
                "title": question["title"],
                "prompt": question["prompt"],
                "score": result["score"],
                "matched_keywords": result["matched_keywords"],
                "missing_keywords": result["missing_keywords"],
            })

        average_score = round(skill_total / max(len(questions), 1))
        rating = score_to_rating(average_score)
        ratings[skill] = rating
        skill_results.append({
            "skill": skill,
            "rating": rating,
            "rating_label": rating_label(rating),
            "average_score": average_score,
            "questions": question_results,
            "missing_concepts": list(dict.fromkeys(missing_concepts))[:5],
        })

    return {
        "ratings": ratings,
        "skill_results": skill_results,
        "overall_score": round(total_score / max(total_questions, 1)),
        "answered_questions": answered_questions,
        "total_questions": total_questions,
    }
