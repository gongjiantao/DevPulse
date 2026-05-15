import os
from collections import defaultdict
from typing import Optional


class CodeStats:
    LANGUAGE_MAP = {
        ".py": "Python",
        ".js": "JavaScript",
        ".ts": "TypeScript",
        ".tsx": "TypeScript React",
        ".jsx": "JavaScript React",
        ".html": "HTML",
        ".css": "CSS",
        ".scss": "SCSS",
        ".java": "Java",
        ".go": "Go",
        ".rs": "Rust",
        ".cpp": "C++",
        ".c": "C",
        ".h": "C Header",
        ".hpp": "C++ Header",
        ".rb": "Ruby",
        ".php": "PHP",
        ".swift": "Swift",
        ".kt": "Kotlin",
        ".md": "Markdown",
        ".json": "JSON",
        ".yaml": "YAML",
        ".yml": "YAML",
        ".xml": "XML",
        ".sql": "SQL",
        ".sh": "Shell",
        ".bat": "Batch",
        ".ps1": "PowerShell",
        ".dockerfile": "Dockerfile",
        ".toml": "TOML",
        ".ini": "INI",
        ".cfg": "Config",
    }

    def __init__(self, repo_path: str = "."):
        self.repo_path = os.path.abspath(repo_path)

    def count_lines(self, file_path: str) -> tuple[int, int, int]:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
            total = len(lines)
            blank = sum(1 for line in lines if line.strip() == "")
            code = total - blank
            return total, code, blank
        except (OSError, UnicodeDecodeError):
            return 0, 0, 0

    def analyze(self, max_file_size_mb: float = 5.0) -> dict:
        languages: dict[str, dict] = defaultdict(
            lambda: {"files": 0, "total_lines": 0,
                     "code_lines": 0, "blank_lines": 0}
        )
        total_files = 0
        total_lines = 0
        total_code_lines = 0
        total_blank_lines = 0

        ignore_dirs = {".git", "__pycache__", "node_modules", ".venv",
                       "venv", "env", ".env", "dist", "build",
                       ".next", ".nuxt", "target", "vendor", ".idea",
                       ".vscode", "coverage", ".pytest_cache"}

        for root, dirs, files in os.walk(self.repo_path):
            dirs[:] = [d for d in dirs if d not in ignore_dirs]

            if ".git" in root.split(os.sep):
                continue

            for file in files:
                file_path = os.path.join(root, file)
                try:
                    file_size = os.path.getsize(file_path)
                    if file_size > max_file_size_mb * 1024 * 1024:
                        continue
                except OSError:
                    continue

                _, ext = os.path.splitext(file)
                language = self.LANGUAGE_MAP.get(ext.lower(), f"Other ({ext or 'no ext'})")

                total, code, blank = self.count_lines(file_path)
                total_files += 1
                total_lines += total
                total_code_lines += code
                total_blank_lines += blank

                languages[language]["files"] += 1
                languages[language]["total_lines"] += total
                languages[language]["code_lines"] += code
                languages[language]["blank_lines"] += blank

        lang_list = [
            {
                "language": lang,
                "files": stats["files"],
                "total_lines": stats["total_lines"],
                "code_lines": stats["code_lines"],
                "blank_lines": stats["blank_lines"],
                "percentage": round(
                    stats["code_lines"] / total_code_lines * 100, 1
                ) if total_code_lines > 0 else 0,
            }
            for lang, stats in languages.items()
        ]
        lang_list.sort(key=lambda x: x["code_lines"], reverse=True)

        return {
            "total_files": total_files,
            "total_lines": total_lines,
            "total_code_lines": total_code_lines,
            "total_blank_lines": total_blank_lines,
            "blank_percentage": round(
                total_blank_lines / total_lines * 100, 1
            ) if total_lines > 0 else 0,
            "languages": lang_list,
        }
