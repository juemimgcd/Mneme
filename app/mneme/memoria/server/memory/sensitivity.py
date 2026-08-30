"""Classify candidate sensitivity and detect secret-like values before memory persistence.

Detection is a conservative policy boundary, not a general-purpose data-loss-prevention engine.
"""

import re

from app.mneme.memoria.server.memory.schemas import SensitivitySignal
from app.mneme.memoria.server.models.memory_candidate import Sensitivity

_SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:[A-Z0-9 ]+ )?PRIVATE KEY-----"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{20,})\b"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{16,}", re.IGNORECASE),
    re.compile(r"\beyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"),
    re.compile(
        r"(?:\b(?:password|passwd|pwd|api[\s_-]?key|access[\s_-]?token|token|secret|"
        r"refresh[\s_-]?token|auth[\s_-]?token|client[\s_-]?secret|private[\s_-]?key)\b|"
        r"(?:密码|密钥|令牌|口令))\s*(?:is|是|为|:|=)\s*"
        r"[\"']?[^\s,;\"']{4,}",
        re.IGNORECASE,
    ),
    re.compile(r"\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?)://[^\s:/]+:[^\s@]+@", re.IGNORECASE),
)

_SECRET_SIGNALS = frozenset(
    {
        "credential",
        "secret",
        "password",
        "api_key",
        "token",
        "access_token",
        "refresh_token",
        "auth_token",
        "client_secret",
        "private_key",
    }
)

_SENSITIVE_PATTERNS = (
    re.compile(r"\b(?:social security|ssn|passport|national id)\b", re.IGNORECASE),
    re.compile(r"(?:身份证|护照)"),
    re.compile(
        r"\b(?:diagnos(?:is|ed)|medical|medication|disease|pregnan\w*|disability|mental health)\b",
        re.IGNORECASE,
    ),
    re.compile(r"(?:病历|诊断|药物|怀孕|残疾|心理健康)"),
    re.compile(
        r"\b(?:bank account|credit card|routing number|iban|income|salary|debt|credit score)\b",
        re.IGNORECASE,
    ),
    re.compile(r"(?:银行卡|信用卡|收入|工资|负债|信用评分)"),
    re.compile(r"\b(?:login|authentication|two-factor|2fa)\b", re.IGNORECASE),
    re.compile(r"(?:登录凭据|身份认证|双重认证)"),
    re.compile(
        r"\b(?:politic(?:al|s)(?: belief| view| affiliation)?|party membership|voting preference)\b",
        re.IGNORECASE,
    ),
    re.compile(r"(?:政治倾向|政治观点|政治立场|政党成员|党员|投票偏好)"),
    re.compile(
        r"\b(?:religion|religious belief|faith|christian(?:ity)?|muslim|islam|jewish|judaism|"
        r"hindu(?:ism)?|buddhis[mt]|atheis[mt])\b",
        re.IGNORECASE,
    ),
    re.compile(r"(?:宗教|信仰|基督徒|基督教|穆斯林|伊斯兰教|犹太教|佛教徒|佛教|印度教|无神论)"),
    re.compile(
        r"\b(?:sexual orientation|gay|lesbian|bisexual|transgender|lgbtq?\+?)\b",
        re.IGNORECASE,
    ),
    re.compile(r"(?:性取向|同性恋|双性恋|跨性别)"),
    re.compile(r"\b(?:race|racial identity|ethnicity|ethnic origin|national origin)\b", re.IGNORECASE),
    re.compile(r"(?:种族|民族|族裔)"),
    re.compile(r"\b(?:trade union|labor union|union membership)\b", re.IGNORECASE),
    re.compile(r"(?:工会成员|工会会籍)"),
    re.compile(r"\b(?:underage|minor)\b", re.IGNORECASE),
    re.compile(r"(?:未成年)"),
    re.compile(
        r"\b(?:home address|residential address|precise location|gps coordinates?|latitude|longitude)\b",
        re.IGNORECASE,
    ),
    re.compile(r"(?:家庭住址|住宅地址|精确位置|实时位置|经纬度)"),
    re.compile(r"\b(?:biometric|facial recognition|genetic|dna profile)\b", re.IGNORECASE),
    re.compile(r"(?:生物特征|人脸识别|基因信息|DNA信息)", re.IGNORECASE),
)


def contains_secret(text: str) -> bool:
    """Return whether text matches the conservative secret-detection boundary.

    The check intentionally favors preventing persistence over recall of
    secret-like strings and runs before external extraction calls.
    """
    return any(pattern.search(text) is not None for pattern in _SECRET_PATTERNS)


def classify_sensitivity(
    *texts: str,
    model_signals: list[SensitivitySignal] | None = None,
) -> Sensitivity:
    """Classify validated candidate text as low, sensitive, or secret.

    The result feeds persistence policy; it is not a complete regulatory or
    enterprise data-classification system.
    """
    signals = set(model_signals or [])
    if any(contains_secret(text) for text in texts) or signals & _SECRET_SIGNALS:
        return "secret"
    if signals or any(
        pattern.search(text) is not None
        for text in texts
        for pattern in _SENSITIVE_PATTERNS
    ):
        return "sensitive"
    return "low"
