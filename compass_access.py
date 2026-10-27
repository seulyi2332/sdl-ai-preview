"""Temporary non-secret evaluation participant labels.

These are PUBLIC, GUESSABLE labels, not authentication.
Only non-sensitive demo exercises should be entered.
Real participant data needs random access tokens and persistent secure storage.
"""
import re

STUDENT_CODES=tuple(f"S{i:02d}" for i in range(1,13))


def is_demo_access_code(code, extra_codes=""):
    code=(code or "").strip()
    if not code or len(code)>40 or not code.isalnum():
        return False
    if code in STUDENT_CODES:
        return True
    if re.fullmatch(r"DEMO[A-Za-z0-9]{0,36}",code):
        return True
    configured={c.strip() for c in (extra_codes or "").replace("\n",",").split(",") if c.strip()}
    return code in configured


def study_id_label(code):
    return ("평가 참여자 "+code) if code in STUDENT_CODES else "개발용 시연 계정"
