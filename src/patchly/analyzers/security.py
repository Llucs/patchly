from __future__ import annotations

from pathlib import Path

from patchly.actions import ActionResult
from patchly.analyzers.base import BaseAnalyzer


SYSTEM = """You are a security code analyzer. Analyze the provided source code and identify:

1. Hardcoded secrets, tokens, API keys, passwords
2. SQL injection vulnerabilities
3. Command injection via user input
4. Path traversal vulnerabilities
5. Insecure cryptography usage
6. Missing input validation
7. Insecure direct object references
8. Cross-site scripting (XSS) in web code
9. Insecure deserialization
10. Privilege escalation risks

For each finding, provide: file path, line numbers, vulnerability type, severity, and remediation.

Output format:
## Vulnerability
- **File**: <path>
- **Type**: <vulnerability class>
- **Severity**: critical/high/medium/low
- **Description**: <what and why>
- **Fix**: <specific remediation>
"""


class SecurityAnalyzer(BaseAnalyzer):
    def analyze(self, files: list[Path]) -> list[ActionResult]:
        content_batches = []
        for f in files:
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
                if text.strip():
                    content_batches.append(f"### {f}\n```\n{text[:3000]}\n```")
            except Exception:
                pass

        if not content_batches:
            return []

        result = self._llm_analysis(SYSTEM, "\n\n".join(content_batches))
        return self._parse_findings(result, "security")
