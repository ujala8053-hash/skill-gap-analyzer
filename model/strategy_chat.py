import re

import pandas as pd

from model.gap_analyzer import analyze_gap


def parse_skills_text(raw_text):
    if not raw_text:
        return []

    cleaned = str(raw_text).replace("\r", "\n").strip()
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


def load_roles_dataframe():
    df = pd.read_csv("dataset/skills.csv")
    df.columns = df.columns.str.strip().str.lower()
    return df


def load_courses_dataframe():
    df = pd.read_csv("dataset/courses.csv")
    df.columns = df.columns.str.strip().str.lower()
    return df


def find_role_record(selected_role):
    if not selected_role:
        return None

    skills_df = load_roles_dataframe()
    matching = skills_df[skills_df["role"].astype(str).str.strip().str.lower() == selected_role.strip().lower()]
    if matching.empty:
        return None

    return matching.iloc[0]


def find_course_recommendations(selected_role):
    if not selected_role:
        return []

    courses_df = load_courses_dataframe()
    role_column = "role" if "role" in courses_df.columns else "pythorole"
    matching = courses_df[courses_df[role_column].astype(str).str.strip().str.lower() == selected_role.strip().lower()]
    if matching.empty:
        return []

    return matching[["course", "platform"]].to_dict(orient="records")


def normalize_message(text):
    return re.sub(r"\s+", " ", str(text or "").strip()).lower()


def infer_focus_topics(message, recent_messages):
    message_text = normalize_message(message)
    combined = message_text
    if not combined:
        combined = " ".join(
            str(item.get("content", ""))
            for item in recent_messages
            if isinstance(item, dict)
        ).lower()

    topics = []
    keyword_topics = [
        ("roadmap", {"roadmap", "plan", "start", "first", "begin", "timeline"}),
        ("projects", {"project", "portfolio", "build", "resume", "showcase"}),
        ("interviews", {"interview", "job", "hiring", "questions", "recruiter"}),
        ("time", {"week", "month", "day", "schedule", "time", "hours"}),
        ("confidence", {"struggle", "stuck", "confused", "overwhelmed", "confidence"}),
        ("courses", {"course", "courses", "resource", "resources", "certification", "certifications"}),
    ]

    for name, keywords in keyword_topics:
        if any(keyword in combined for keyword in keywords):
            topics.append(name)

    return topics


def detect_question_intent(message, recent_messages):
    message_text = normalize_message(message)
    if not message_text:
        message_text = " ".join(
            str(item.get("content", ""))
            for item in recent_messages
            if isinstance(item, dict)
        ).lower()

    intent_rules = [
        ("courses", {"course", "courses", "resource", "resources", "certification", "certifications", "learn from"}),
        ("projects", {"project", "portfolio", "build", "showcase", "resume"}),
        ("interviews", {"interview", "interviews", "hiring", "recruiter", "job questions", "mock interview"}),
        ("priority_skills", {"learn first", "skill first", "skills first", "close the gap", "priority", "focus on first", "what should i learn"}),
        ("roadmap", {"roadmap", "plan", "timeline", "30-day", "30 day", "60-day", "60 day", "90-day", "90 day", "6-week", "6 week"}),
        ("match", {"match", "fit", "ready", "qualified", "how close", "am i ready"}),
        ("time", {"schedule", "week", "weeks", "month", "months", "hours per day", "hours per week"}),
        ("confidence", {"stuck", "confused", "overwhelmed", "confidence", "worried"}),
    ]

    for intent, keywords in intent_rules:
        if any(keyword in message_text for keyword in keywords):
            return intent

    return "general"


def extract_timeframe(message):
    match = re.search(r"(\d+)\s*[- ]?\s*(day|days|week|weeks|month|months)", str(message or ""), re.IGNORECASE)
    if not match:
        return ""

    amount = match.group(1)
    unit = match.group(2).lower()
    if amount == "1" and unit.endswith("s"):
        unit = unit[:-1]
    return f"{amount} {unit}"


def format_skill_list(skills, limit=3, fallback="none yet"):
    cleaned = [str(skill).strip() for skill in (skills or []) if str(skill).strip()]
    return ", ".join(cleaned[:limit]) if cleaned else fallback


def role_project_idea(selected_role, strengths, missing_skills):
    role_key = selected_role.strip().lower()
    project_map = {
        "data analyst": "Build a dashboard that cleans a CSV dataset, tracks KPIs, and explains the business insight behind each chart.",
        "data scientist": "Create an end-to-end prediction notebook with data cleaning, feature engineering, evaluation, and a short business recommendation.",
        "ml engineer": "Package a small model as an API and add basic monitoring or retraining notes to show deployment thinking.",
        "frontend developer": "Design a polished responsive interface with live filtering, charts, and careful interaction states.",
        "backend developer": "Ship a REST API with authentication, validation, and database-backed endpoints for a realistic product workflow.",
        "web developer": "Build a full-stack feature with a clean UI, form validation, and a small dashboard to demonstrate product sense.",
        "software engineer": "Create a mini product with solid data structures, tests, and a short architecture note in the README.",
        "devops engineer": "Set up CI for a demo app, containerize it, and document a deployment pipeline with environment separation.",
        "ai engineer": "Build an applied AI demo with a clear user problem, preprocessing, model output explanation, and evaluation notes.",
        "cloud engineer": "Deploy a small web service using managed cloud resources and document the architecture, security, and cost tradeoffs.",
    }

    idea = project_map.get(role_key)
    if idea:
        return idea

    focus_skills = strengths[:1] + missing_skills[:2]
    if focus_skills:
        return "Build one focused portfolio piece that proves your ability in " + ", ".join(focus_skills) + "."

    return "Build a small real-world project that demonstrates one technical skill and one problem-solving skill."


def build_next_steps(intent, focus_topics, matched_skills, missing_skills, course_recommendations, selected_role, timeframe):
    steps = []
    focus_skills = missing_skills[:3] or matched_skills[:3]

    if intent == "priority_skills":
        if missing_skills:
            steps.append(f"Start with {missing_skills[0]}, because it is a direct requirement for {selected_role}.")
        elif matched_skills:
            steps.append(f"Turn {matched_skills[0]} into stronger proof with one measurable project or case study.")
    elif intent == "projects":
        steps.append(role_project_idea(selected_role, matched_skills, missing_skills))
        steps.append("Finish the project with a short README that explains the problem, your approach, and the result.")
    elif intent == "interviews":
        steps.append("Practice one technical explanation and one project walkthrough each week so your answers become clearer and faster.")
        steps.append("Build a short story bank around challenges, decisions, tradeoffs, and outcomes from your work.")
    elif intent == "courses":
        if course_recommendations:
            first_course = course_recommendations[0]
            steps.append(f"Use {first_course['course']} on {first_course['platform']} as your structured foundation.")
        else:
            steps.append("Use one structured course only as support and keep most of your time on hands-on practice.")
        steps.append("After each module, build one small artifact so the course turns into portfolio proof.")
    elif intent in {"roadmap", "time"}:
        sprint_label = timeframe or "the next few weeks"
        if focus_skills:
            steps.append(f"For {sprint_label}, focus on {format_skill_list(focus_skills, limit=2, fallback='one core skill')} before adding anything new.")
        else:
            steps.append(f"For {sprint_label}, keep the plan narrow and measure progress with one visible deliverable each week.")
        steps.append("Split the week into learning, practice, and review so progress stays realistic.")
    else:
        if missing_skills:
            steps.append(f"Prioritize {format_skill_list(missing_skills)} first, because those are the clearest gaps for {selected_role}.")
        elif matched_skills:
            steps.append(f"Double down on {format_skill_list(matched_skills)} and turn them into stronger proof through projects or interview stories.")
        else:
            steps.append("Start by listing the 3 to 5 skills you already use confidently so your plan has a realistic starting point.")

    if not any(step.startswith("Build") for step in steps) and ("projects" in focus_topics or intent == "general"):
        steps.append(role_project_idea(selected_role, matched_skills, missing_skills))

    if intent not in {"interviews", "time", "roadmap"}:
        if "interviews" in focus_topics:
            steps.append("Set aside one session each week for mock interview answers, role-specific questions, and explaining past work clearly.")
        elif "time" in focus_topics:
            steps.append("Use a light weekly rhythm: learn on one day, practice on another, and review with a small deliverable before the weekend.")
        else:
            steps.append("Use a cycle of learn, apply, and review so each new concept becomes something visible in your portfolio.")

    if course_recommendations:
        first_course = course_recommendations[0]
        steps.append(f"Use {first_course['course']} on {first_course['platform']} as structured support, but pair it with hands-on practice every week.")

    return steps[:4]


def build_intro(intent, selected_role, timeframe):
    role_name = selected_role or "your target role"

    if intent == "priority_skills":
        return f"For {role_name}, the best skills to learn first are the ones that unlock role fit fastest."
    if intent == "projects":
        return f"For {role_name}, the strongest next move is to build one project that proves the right skills."
    if intent == "interviews":
        return f"For {role_name}, interview prep should stay tied to your actual projects and skill gaps."
    if intent == "courses":
        return f"For {role_name}, the course choice matters less than how you turn it into practice."
    if intent == "roadmap":
        return f"For {role_name}, here is a practical roadmap{f' for {timeframe}' if timeframe else ''}."
    if intent == "time":
        return f"For {role_name}, a lighter schedule will work better than a plan that is too wide."
    if intent == "match":
        return f"For {role_name}, here is how close your current profile looks right now."
    if intent == "confidence":
        return f"For {role_name}, keep the next step small enough that you can actually sustain it."
    return f"For {role_name}, here is the clearest next move based on what you shared."


def build_question_specific_lines(intent, selected_role, known_skills, match, matched_skills, missing_skills, course_recommendations, timeframe):
    role_name = selected_role or "your target role"
    lines = []

    if intent == "priority_skills":
        if missing_skills:
            first_skill = missing_skills[0]
            second_skill = missing_skills[1] if len(missing_skills) > 1 else None
            lines.append(f"Start with {first_skill} first, because it is currently missing and directly affects your fit for {role_name}.")
            if second_skill:
                lines.append(f"After that, move to {second_skill} so your profile stops looking one-dimensional.")
        elif matched_skills:
            lines.append(f"You already cover the core stack in {format_skill_list(matched_skills)}. The next step is deeper proof, not random new tools.")
        else:
            lines.append("List a few current skills first so the coach can rank your gaps more accurately.")
    elif intent == "projects":
        lines.append(role_project_idea(role_name, matched_skills, missing_skills))
        if missing_skills:
            lines.append(f"Make sure the project visibly includes {format_skill_list(missing_skills, limit=2)} so it closes a real gap, not just a comfort-zone gap.")
    elif intent == "interviews":
        if matched_skills:
            lines.append(f"Lead with examples around {format_skill_list(matched_skills, limit=2)}, because those are already in your stack.")
        if missing_skills:
            lines.append(f"Prepare short learning narratives for {format_skill_list(missing_skills, limit=2)}, so you can explain how you are actively closing those gaps.")
        lines.append("Strong interview answers usually follow a simple structure: problem, approach, tradeoff, and result.")
    elif intent == "courses":
        if course_recommendations:
            first_course = course_recommendations[0]
            lines.append(f"The best structured resource from your dataset is {first_course['course']} on {first_course['platform']}.")
            lines.append("Use it to organize your learning, but do not let the certificate become the goal.")
        else:
            lines.append("There is no course mapped for that role in the current dataset, so focus on one practical project plus one trusted learning resource.")
    elif intent == "roadmap":
        sprint_label = timeframe or "the next 4 to 6 weeks"
        lines.append(f"Treat {sprint_label} as a short sprint with one foundation phase, one build phase, and one review phase.")
        if missing_skills:
            lines.append(f"In the foundation phase, focus on {format_skill_list(missing_skills, limit=2)} before expanding your scope.")
    elif intent == "time":
        sprint_label = timeframe or "each week"
        lines.append(f"A realistic plan for {sprint_label} is better than an ambitious plan that breaks after a few days.")
        lines.append("Keep each study block small, and make every week end with one visible output.")
    elif intent == "match":
        lines.append(f"Your current alignment is about {match}% for {role_name}.")
        if missing_skills:
            lines.append(f"The biggest gaps still affecting that match are {format_skill_list(missing_skills)}.")
        elif matched_skills:
            lines.append(f"Your strongest overlap is in {format_skill_list(matched_skills)}.")
    elif intent == "confidence":
        lines.append("Do not try to fix everything at once. Pick one skill, one deliverable, and one weekly review point.")
        if missing_skills:
            lines.append(f"If you want the safest starting point, begin with {missing_skills[0]} and keep the rest parked for later.")
    else:
        if selected_role and known_skills:
            lines.append(
                f"Your current alignment is about {match}% with strong overlap in {format_skill_list(matched_skills)}."
            )
        elif known_skills:
            lines.append(f"You already have momentum in {format_skill_list(known_skills)}. We can build from that foundation.")
        else:
            lines.append("Add your current skills in the dashboard form to make the guidance more targeted.")

        if missing_skills:
            lines.append(f"The biggest gaps to close next are {format_skill_list(missing_skills)}.")

    return lines


def build_reply(message, selected_role, known_skills, match, matched_skills, missing_skills, course_recommendations, focus_topics, intent, timeframe):
    lines = []
    lines.append(build_intro(intent, selected_role, timeframe))
    lines.extend(
        build_question_specific_lines(
            intent=intent,
            selected_role=selected_role,
            known_skills=known_skills,
            match=match,
            matched_skills=matched_skills,
            missing_skills=missing_skills,
            course_recommendations=course_recommendations,
            timeframe=timeframe,
        )
    )

    if "confidence" in focus_topics:
        lines.append("Keep the scope tight for now. One visible weekly win is more valuable than a broad plan you cannot sustain.")
    elif intent == "roadmap" or "roadmap" in focus_topics:
        lines.append("Think in short sprints: foundation first, proof next, and interview readiness after that.")
    elif intent == "interviews" or "interviews" in focus_topics:
        lines.append("Frame every study block around explainability, because employers will care about how you think as much as what you know.")
    elif intent == "projects" or "projects" in focus_topics:
        lines.append("Your portfolio should show applied judgment, not just course completion, so optimize for one meaningful project over many small clones.")
    elif intent == "courses":
        lines.append("A course only helps if you can translate each lesson into a small piece of visible work.")
    else:
        lines.append("The fastest progress usually comes from learning only the skills that unlock the next credible project.")

    next_steps = build_next_steps(
        intent=intent,
        focus_topics=focus_topics,
        matched_skills=matched_skills,
        missing_skills=missing_skills,
        course_recommendations=course_recommendations,
        selected_role=selected_role or "your target role",
        timeframe=timeframe,
    )

    if next_steps:
        lines.append("")
        lines.append("Recommended next steps:")
        for index, step in enumerate(next_steps, start=1):
            lines.append(f"{index}. {step}")

    if course_recommendations:
        first_course = course_recommendations[0]
        lines.append("")
        lines.append(f"Best structured resource from your dataset: {first_course['course']} ({first_course['platform']}).")

    return "\n".join(lines)


def generate_strategy_reply(message, selected_role="", raw_skills="", recent_messages=None):
    recent_messages = recent_messages or []
    cleaned_message = str(message).strip()
    known_skills = parse_skills_text(raw_skills)

    role_record = find_role_record(selected_role)
    role_skills = parse_role_skills(role_record["skills"]) if role_record is not None else []
    match = 0
    missing_skills = []
    matched_skills = []

    if selected_role:
        match, missing_skills, matched_skills = analyze_gap(raw_skills, selected_role)

    course_recommendations = find_course_recommendations(selected_role)
    focus_topics = infer_focus_topics(cleaned_message, recent_messages)
    intent = detect_question_intent(cleaned_message, recent_messages)
    timeframe = extract_timeframe(cleaned_message)

    if selected_role and role_record is None:
        role_hint = f"I could not find '{selected_role}' in the current role dataset, so the advice stays more general for now."
    elif not selected_role and role_record is None:
        role_hint = "Select a target role in the dashboard for role-specific advice."
    else:
        role_hint = ""

    reply = build_reply(
        message=cleaned_message,
        selected_role=selected_role,
        known_skills=known_skills,
        match=match,
        matched_skills=matched_skills,
        missing_skills=missing_skills,
        course_recommendations=course_recommendations,
        focus_topics=focus_topics,
        intent=intent,
        timeframe=timeframe,
    )

    if role_hint:
        reply = f"{reply}\n\n{role_hint}".strip()

    follow_up_prompts = {
        "priority_skills": [
            "Give me a 30-day plan for these priority skills.",
            "Which project can prove these skills fastest?",
            "How do I practice these skills every week?",
        ],
        "projects": [
            "Break this project into weekly milestones.",
            "What should I include in the README and portfolio write-up?",
            "How do I explain this project in interviews?",
        ],
        "interviews": [
            "Give me role-specific interview questions to practice.",
            "How should I explain weak areas honestly?",
            "What project stories should I prepare first?",
        ],
        "courses": [
            "How do I turn this course into portfolio proof?",
            "What should I build alongside this course?",
            "What should I learn after this resource?",
        ],
        "roadmap": [
            "Turn this roadmap into a weekly checklist.",
            "What should I build by the end of this plan?",
            "Which skills should I review first before starting?",
        ],
    }.get(
        intent,
        [
            "Give me a 30-day execution plan.",
            "Suggest one project that proves this role fit.",
            "How should I prepare for interviews next?",
        ],
    )

    return {
        "reply": reply,
        "summary": {
            "role": selected_role or "Not selected",
            "match": match,
            "strengths": matched_skills[:3] or known_skills[:3],
            "priority_skills": missing_skills[:3] or role_skills[:3],
            "recommended_course": (
                f"{course_recommendations[0]['course']} ({course_recommendations[0]['platform']})"
                if course_recommendations else "Add a target role to get a course recommendation"
            ),
        },
        "follow_up_prompts": follow_up_prompts,
    }
