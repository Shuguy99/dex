import logging
from typing import Any

logger = logging.getLogger("dex.learning.constitution")

CONSTITUTION = [
    {
        "id": "privacy_1",
        "principle": "Никогда не передавай личные данные пользователя внешним сервисам без явного разрешения.",
        "check": "personal_data_exfiltration",
        "severity": "critical"
    },
    {
        "id": "safety_1",
        "principle": "Не выполняй команды, которые могут повредить операционную систему или файлы.",
        "check": "system_harm",
        "severity": "critical"
    },
    {
        "id": "autonomy_1",
        "principle": "Не изменяй собственный исходный код без явного подтверждения пользователя.",
        "check": "self_modification",
        "severity": "high"
    },
    {
        "id": "honesty_1",
        "principle": "Не выдавай себя за человека и не вводи пользователя в заблуждение.",
        "check": "deception",
        "severity": "high"
    },
    {
        "id": "security_1",
        "principle": "Все чувствительные данные должны храниться только в зашифрованном виде.",
        "check": "encryption",
        "severity": "high"
    },
    {
        "id": "memory_1",
        "principle": "Не записывай в долговременную память информацию, помеченную пользователем как временная.",
        "check": "memory_retention",
        "severity": "medium"
    },
    {
        "id": "resource_1",
        "principle": "Не расходуй ресурсы системы (CPU, RAM, диск) без необходимости.",
        "check": "resource_waste",
        "severity": "medium"
    },
    {
        "id": "ethics_1",
        "principle": "Отказывайся выполнять команды, которые могут навредить другим людям.",
        "check": "harm_to_others",
        "severity": "critical"
    },
]


class ConstitutionalChecker:
    def __init__(self) -> None:
        self._constitution = CONSTITUTION

    def check_action(self, action: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        violations = []
        action_lower = action.lower()
        params = params or {}

        for article in self._constitution:
            check = article["check"]
            violated = False

            if check == "personal_data_exfiltration":
                if any(kw in action_lower for kw in ["send", "upload", "share", "отправить"]):
                    if any(k in str(params.values()) for k in
                           ["password", "token", "secret", "пароль"]):
                        violated = True

            elif check == "system_harm":
                if any(kw in action_lower for kw in ["delete", "remove", "rm", "format",
                                                      "del", "удали", "удалить"]):
                    target = str(params.get("path", params.get("name", "")))
                    if any(p in target.lower() for p in
                           ["windows", "system32", "boot", "/dev/", "/etc/"]):
                        violated = True

            elif check == "self_modification":
                if any(kw in action_lower for kw in
                       ["self_heal", "modify_code", "update_source", "rewrite"]):
                    violated = True

            elif check == "deception":
                if any(kw in action_lower for kw in ["pretend", "impersonate", "fake"]):
                    violated = True

            elif check == "encryption":
                if any(kw in action_lower for kw in ["store", "save", "save_secure"]):
                    value = str(params.values())
                    if any(k in value for k in
                           ["password", "пароль", "secret", "token", "credit"]):
                        if "secure" not in action_lower and "encrypt" not in action_lower:
                            violated = True

            elif check == "resource_waste":
                if any(kw in action_lower for kw in
                       ["loop", "infinite", "while_true", "fork_bomb"]):
                    violated = True

            elif check == "harm_to_others" and any(kw in action_lower for kw in
                   ["ddos", "hack", "crack", "exploit", "malware", "virus"]):
                violated = True

            if violated:
                violations.append({
                    "article": article["id"],
                    "principle": article["principle"],
                    "severity": article["severity"],
                    "blocked": article["severity"] in ("critical", "high")
                })

        return violations

    def can_proceed(self, action: str, params: dict[str, Any] | None = None) -> tuple[bool, list[str]]:
        violations = self.check_action(action, params)
        blocked = [v for v in violations if v["blocked"]]
        if blocked:
            reasons = [
                f"[{v['severity'].upper()}] {v['principle']}"
                for v in blocked
            ]
            return False, reasons
        return True, []

    def get_articles(self, severity: str | None = None) -> list[dict[str, Any]]:
        if severity:
            return [a for a in self._constitution if a["severity"] == severity]
        return list(self._constitution)

    def explain(self, article_id: str) -> str | None:
        for a in self._constitution:
            if a["id"] == article_id:
                return a["principle"]
        return None
