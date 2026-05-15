import subprocess
import os
from datetime import datetime, timedelta
from typing import Optional
from collections import defaultdict

class GitAnalyzer:
    def __init__(self, repo_path: str = "."):
        self.repo_path = os.path.abspath(repo_path)

    def _run_git(self, args: list[str]) -> str:
        try:
            result = subprocess.run(
                ["git"] + args,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=30,
            )
            result.check_returncode()
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return ""
        except (FileNotFoundError, NotADirectoryError, OSError):
            raise RuntimeError("Git 命令执行失败，请检查路径是否正确")

    def is_git_repo(self) -> bool:
        try:
            result = self._run_git(["rev-parse", "--git-dir"])
            return bool(result)
        except RuntimeError:
            return False

    def get_commit_count(self) -> int:
        output = self._run_git(["rev-list", "--count", "HEAD"])
        return int(output) if output.isdigit() else 0

    def get_contributors(self) -> list[dict]:
        output = self._run_git([
            "shortlog", "-sne", "HEAD", "--all"
        ])
        contributors = []
        if not output:
            return contributors
        for line in output.split("\n"):
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) < 2:
                continue
            count_str = parts[0].strip()
            name_email = parts[1].strip()
            email = ""
            name = name_email
            if "<" in name_email and ">" in name_email:
                name, email_part = name_email.rsplit("<", 1)
                name = name.strip()
                email = email_part.rstrip(">").strip()

            commits = int(count_str) if count_str.isdigit() else 0
            contributors.append({
                "name": name,
                "email": email,
                "commits": commits,
            })
        contributors.sort(key=lambda x: x["commits"], reverse=True)
        return contributors

    def get_commit_activity(self, days: int = 90) -> list[dict]:
        since_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        output = self._run_git([
            "log", "--since", since_date, "--format=%ad",
            "--date=short", "HEAD"
        ])
        if not output:
            return []
        date_counts: dict[str, int] = defaultdict(int)
        for line in output.split("\n"):
            line = line.strip()
            if line:
                date_counts[line] += 1

        result = []
        current = datetime.now().date()
        for i in range(days):
            d = current - timedelta(days=days - 1 - i)
            date_str = d.strftime("%Y-%m-%d")
            result.append({
                "date": date_str,
                "commits": date_counts.get(date_str, 0),
            })
        return result

    def get_code_churn(self) -> dict:
        output = self._run_git([
            "log", "--format=", "--numstat", "HEAD"
        ])
        total_added = 0
        total_deleted = 0
        file_changes: dict[str, dict] = defaultdict(
            lambda: {"added": 0, "deleted": 0, "commits": 0}
        )
        if not output:
            return {
                "total_added": 0,
                "total_deleted": 0,
                "net_change": 0,
                "files": [],
            }
        for line in output.split("\n"):
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) < 3:
                continue
            added_str, deleted_str, filename = parts[0], parts[1], parts[2]
            try:
                added = int(added_str) if added_str != "-" else 0
                deleted = int(deleted_str) if deleted_str != "-" else 0
            except ValueError:
                continue
            total_added += added
            total_deleted += deleted
            file_changes[filename]["added"] += added
            file_changes[filename]["deleted"] += deleted
            file_changes[filename]["commits"] += 1

        files = [
            {
                "filename": fname,
                "added": stats["added"],
                "deleted": stats["deleted"],
                "net": stats["added"] - stats["deleted"],
                "commits": stats["commits"],
            }
            for fname, stats in file_changes.items()
        ]
        files.sort(key=lambda x: x["added"] + x["deleted"], reverse=True)

        return {
            "total_added": total_added,
            "total_deleted": total_deleted,
            "net_change": total_added - total_deleted,
            "files": files[:50],
        }

    def get_branch_info(self) -> dict:
        current_branch = self._run_git(
            ["rev-parse", "--abbrev-ref", "HEAD"]
        )
        all_branches = self._run_git(["branch", "-a"])
        branch_list = []
        if all_branches:
            for line in all_branches.split("\n"):
                line = line.strip().replace("*", "").strip()
                if line and not line.startswith("remotes/"):
                    branch_list.append(line)
        count = len(branch_list) if branch_list else 1
        return {
            "current_branch": current_branch or "main",
            "branch_count": count,
            "branches": branch_list[:20],
        }

    def get_file_type_distribution(self) -> list[dict]:
        extensions: dict[str, int] = defaultdict(int)
        total_files = 0
        for root, dirs, files in os.walk(self.repo_path):
            if ".git" in root:
                continue
            for file in files:
                _, ext = os.path.splitext(file)
                if ext:
                    extensions[ext] += 1
                else:
                    extensions["(no extension)"] += 1
                total_files += 1

        result = [
            {"extension": ext, "count": count,
             "percentage": round(count / total_files * 100, 1) if total_files > 0 else 0}
            for ext, count in extensions.items()
        ]
        result.sort(key=lambda x: x["count"], reverse=True)
        return result[:15]

    def get_full_stats(self) -> dict:
        if not self.is_git_repo():
            return {"error": "Not a git repository",
                    "is_git_repo": False}

        return {
            "is_git_repo": True,
            "repo_path": self.repo_path,
            "commit_count": self.get_commit_count(),
            "contributors": self.get_contributors(),
            "commit_activity": self.get_commit_activity(),
            "code_churn": self.get_code_churn(),
            "branch_info": self.get_branch_info(),
            "file_types": self.get_file_type_distribution(),
        }
