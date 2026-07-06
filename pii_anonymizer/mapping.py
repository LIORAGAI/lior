"""ניהול מיפוי בין ערכים מקוריים (PII) לקודים אנונימיים, ושמירתו כקובץ מקומי בלבד."""
import json
from pathlib import Path

CODE_PREFIXES = {
    "ID": "ID",
    "COMPANY_ID": "COMP",
    "NAME": "NAME",
    "COMPANY_NAME": "CONAME",
    "PHONE": "PHONE",
    "EMAIL": "EMAIL",
    "ADDRESS": "ADDR",
    "GENERIC": "VAL",
}


class CodeMapper:
    """ממיר ערכים מזוהים לקודים, תוך שמירה על עקביות - אותו ערך מקורי תמיד יקבל אותו קוד."""

    def __init__(self):
        self._value_to_code: dict[tuple[str, str], str] = {}
        self._code_to_value: dict[str, str] = {}
        self._counters: dict[str, int] = {}

    def encode(self, pii_type: str, value: str) -> str:
        key = (pii_type, value)
        if key in self._value_to_code:
            return self._value_to_code[key]
        prefix = CODE_PREFIXES.get(pii_type, "VAL")
        self._counters[prefix] = self._counters.get(prefix, 0) + 1
        code = f"[[{prefix}_{self._counters[prefix]:04d}]]"
        self._value_to_code[key] = code
        self._code_to_value[code] = value
        return code

    def to_dict(self) -> dict:
        return {
            "entries": [
                {"type": t, "original": v, "code": c}
                for (t, v), c in self._value_to_code.items()
            ]
        }

    def to_json_str(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    def save(self, path: str):
        Path(path).write_text(self.to_json_str(), encoding="utf-8")

    @classmethod
    def from_dict(cls, data: dict) -> "CodeMapper":
        mapper = cls()
        for entry in data["entries"]:
            key = (entry["type"], entry["original"])
            mapper._value_to_code[key] = entry["code"]
            mapper._code_to_value[entry["code"]] = entry["original"]
        return mapper

    @classmethod
    def load(cls, path: str) -> "CodeMapper":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    def code_to_value_map(self) -> dict:
        return dict(self._code_to_value)
