import re

import pandas as pd


def _normalize_skill(skill):
    return re.sub(r"[^a-z0-9]+", "", str(skill).strip().lower())


def _parse_user_skills(user_skills):
    if isinstance(user_skills, dict):
        return {str(skill).strip() for skill in user_skills.keys() if str(skill).strip()}

    raw_text = str(user_skills or "").replace("\r", "\n").strip()
    if not raw_text:
        return set()

    if "," in raw_text or "\n" in raw_text:
        parts = re.split(r"[\n,]+", raw_text)
    else:
        parts = raw_text.split()

    return {part.strip() for part in parts if part.strip()}


def analyze_gap(user_skills, selected_role):
    df = pd.read_csv("dataset/skills.csv")
    role_data = df[df["Role"].astype(str).str.strip().str.lower() == str(selected_role).strip().lower()]

    if role_data.empty:
        return 0, [], []

    required_skills = [
        skill for skill in re.split(r"[\s,]+", str(role_data.iloc[0]["Skills"]).strip())
        if skill
    ]
    normalized_user_skills = {
        _normalize_skill(skill)
        for skill in _parse_user_skills(user_skills)
    }

    matched = []
    missing = []

    for skill in required_skills:
        if _normalize_skill(skill) in normalized_user_skills:
            matched.append(skill)
        else:
            missing.append(skill)

    match_percentage = round((len(matched) / len(required_skills)) * 100) if required_skills else 0

    return match_percentage, missing, matched
