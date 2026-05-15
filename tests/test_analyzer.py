import pytest
import os
import tempfile
import subprocess

from src.analyzer.git_analyzer import GitAnalyzer
from src.analyzer.code_stats import CodeStats


@pytest.fixture
def temp_git_repo():
    with tempfile.TemporaryDirectory() as tmpdir:
        subprocess.run(["git", "init"], cwd=tmpdir,
                       capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"],
                       cwd=tmpdir, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Test User"],
                       cwd=tmpdir, capture_output=True, check=True)

        with open(os.path.join(tmpdir, "README.md"), "w") as f:
            f.write("# Test Repo\n\nThis is a test repository.\n")
        with open(os.path.join(tmpdir, "main.py"), "w") as f:
            f.write("def hello():\n    print('Hello World')\n\n\nif __name__ == '__main__':\n    hello()\n")

        subprocess.run(["git", "add", "."], cwd=tmpdir,
                       capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"],
                       cwd=tmpdir, capture_output=True, check=True)

        with open(os.path.join(tmpdir, "main.py"), "a") as f:
            f.write("\ndef goodbye():\n    print('Goodbye')\n")
        subprocess.run(["git", "add", "main.py"],
                       cwd=tmpdir, capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "Add goodbye function"],
                       cwd=tmpdir, capture_output=True, check=True)

        yield tmpdir


class TestGitAnalyzer:
    def test_is_git_repo_positive(self, temp_git_repo):
        analyzer = GitAnalyzer(temp_git_repo)
        assert analyzer.is_git_repo() is True

    def test_is_git_repo_negative(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            analyzer = GitAnalyzer(tmpdir)
            assert analyzer.is_git_repo() is False

    def test_get_commit_count(self, temp_git_repo):
        analyzer = GitAnalyzer(temp_git_repo)
        assert analyzer.get_commit_count() == 2

    def test_get_contributors(self, temp_git_repo):
        analyzer = GitAnalyzer(temp_git_repo)
        contributors = analyzer.get_contributors()
        assert len(contributors) == 1
        assert contributors[0]["name"] == "Test User"
        assert contributors[0]["commits"] == 2

    def test_get_commit_activity(self, temp_git_repo):
        analyzer = GitAnalyzer(temp_git_repo)
        activity = analyzer.get_commit_activity(days=7)
        assert len(activity) == 7
        total = sum(a["commits"] for a in activity)
        assert total == 2

    def test_get_code_churn(self, temp_git_repo):
        analyzer = GitAnalyzer(temp_git_repo)
        churn = analyzer.get_code_churn()
        assert churn["total_added"] > 0
        assert "files" in churn

    def test_get_branch_info(self, temp_git_repo):
        analyzer = GitAnalyzer(temp_git_repo)
        branch_info = analyzer.get_branch_info()
        assert "current_branch" in branch_info
        assert branch_info["branch_count"] >= 1

    def test_get_file_type_distribution(self, temp_git_repo):
        analyzer = GitAnalyzer(temp_git_repo)
        file_types = analyzer.get_file_type_distribution()
        assert len(file_types) >= 2
        exts = [ft["extension"] for ft in file_types]
        assert ".md" in exts
        assert ".py" in exts

    def test_get_full_stats(self, temp_git_repo):
        analyzer = GitAnalyzer(temp_git_repo)
        stats = analyzer.get_full_stats()
        assert stats["is_git_repo"] is True
        assert stats["commit_count"] == 2
        assert len(stats["contributors"]) == 1
        assert len(stats["commit_activity"]) == 90
        assert stats["code_churn"]["total_added"] > 0
        assert "branch_info" in stats
        assert len(stats["file_types"]) >= 2

    def test_full_stats_non_repo(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            analyzer = GitAnalyzer(tmpdir)
            stats = analyzer.get_full_stats()
            assert stats["is_git_repo"] is False


class TestCodeStats:
    def test_count_lines(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "test.py")
            with open(file_path, "w") as f:
                f.write("def foo():\n    pass\n\n\ndef bar():\n    pass\n")
            stats = CodeStats(tmpdir)
            total, code, blank = stats.count_lines(file_path)
            assert total == 6
            assert code == 4
            assert blank == 2

    def test_analyze(self, temp_git_repo):
        stats = CodeStats(temp_git_repo)
        result = stats.analyze()
        assert result["total_files"] == 2
        assert result["total_lines"] > 0
        assert result["total_code_lines"] > 0
        assert len(result["languages"]) >= 2

    def test_analyze_empty_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            stats = CodeStats(tmpdir)
            result = stats.analyze()
            assert result["total_files"] == 0
            assert result["total_lines"] == 0
            assert result["languages"] == []
