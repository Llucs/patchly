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
    def analyze(
        self,
        file_contents: str,
        file_path: Path | None = None,
    ) -> list[ActionResult]:
        if not file_contents or not file_contents.strip():
            return []

        display_path = file_path or Path("<unknown>")
        content_batches = [f"### {display_path}\n```\n{file_contents[:3000]}\n```"]

        result = self._llm_analysis(SYSTEM, "\n\n".join(content_batches))
        return self._parse_findings(result, "security")