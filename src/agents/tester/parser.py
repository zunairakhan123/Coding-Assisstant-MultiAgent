import re
from pydantic import BaseModel
from typing import Optional

class TestErrorSignature(BaseModel):
    """Normalized, deterministic fingerprint of an execution failure."""
    error_type: str
    test_name: Optional[str] = "global"
    file: Optional[str] = "unknown"
    normalized_message: str

    @property
    def fingerprint_key(self) -> str:
        """Generates a canonical, line-number-agnostic error key."""
        clean_type = self.error_type.strip()
        clean_test = (self.test_name or "global").strip()
        clean_msg = self.normalized_message.strip()
        return f"{clean_type}::{clean_test}::{clean_msg}"

class TestErrorParser:
    """Extracts and normalizes failure signatures from Pytest / Traceback outputs."""

    # Regex patterns for stripping volatile noise
    HEX_PATTERN = re.compile(r"0x[0-9a-fA-F]+")
    UUID_PATTERN = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
    PATH_LINE_PATTERN = re.compile(r"(?:/[^:\s]+|C:\\[^:\s]+):(?:\d+:)?\d*")
    LINE_NO_PATTERN = re.compile(r"line \d+", re.IGNORECASE)
    TIME_PATTERN = re.compile(r"\b\d+(?:\.\d+)?s\b|\b\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}\b")

    @classmethod
    def normalize_text(cls, text: str) -> str:
        """Sanitizes text by removing volatile runtime artifacts."""
        text = cls.HEX_PATTERN.sub("<HEX>", text)
        text = cls.UUID_PATTERN.sub("<UUID>", text)
        text = cls.PATH_LINE_PATTERN.sub("<PATH>", text)
        text = cls.LINE_NO_PATTERN.sub("<LINE>", text)
        text = cls.TIME_PATTERN.sub("<TIME>", text)
        return " ".join(text.split())  # Normalize whitespace

    @classmethod
    def parse_pytest_output(cls, raw_output: str) -> TestErrorSignature:
        """Parses Pytest failure blocks into a structured TestErrorSignature."""
        lines = [line.strip() for line in raw_output.split("\n") if line.strip()]
        if not lines:
            return TestErrorSignature(
                error_type="UnknownError",
                normalized_message="Empty execution log"
            )

        error_type = "AssertionError"
        test_name = "test_execution"
        file_name = "test_main.py"
        raw_msg = lines[-1]

        # Extract Pytest failure header (e.g., "_____ test_health_endpoint _____")
        for line in lines:
            if line.startswith("____") and line.endswith("____"):
                test_name = line.strip("_ ").strip()
                break

        # Extract explicit exception details if present
        for line in reversed(lines):
            if "Error:" in line or "Exception:" in line or "FAILED" in line:
                parts = line.split(":", 1)
                if len(parts) == 2 and " " not in parts[0]:
                    error_type = parts[0].strip()
                    raw_msg = parts[1].strip()
                else:
                    raw_msg = line
                break

        normalized_msg = cls.normalize_text(raw_msg)

        return TestErrorSignature(
            error_type=error_type,
            test_name=test_name,
            file=file_name,
            normalized_message=normalized_msg
        )