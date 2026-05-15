from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import re
import tempfile
import subprocess

from .analyzer.git_analyzer import GitAnalyzer
from .analyzer.code_stats import CodeStats
from .utils.helpers import get_utc_timestamp

CLONED_REPOS: dict[str, str] = {}

GITHUB_URL_PATTERN = re.compile(
    r"^https?://(github\.com|gitlab\.com|bitbucket\.org|gitee\.com)/[^/]+/[^/]+(\.git)?$"
)


def resolve_repo_path(raw: str) -> str:
    raw = raw.strip()
    if GITHUB_URL_PATTERN.match(raw):
        if not raw.endswith(".git"):
            raw = raw.rstrip("/") + ".git"
        if raw in CLONED_REPOS:
            return CLONED_REPOS[raw]
        tmpdir = tempfile.mkdtemp(prefix="devpulse_")
        try:
            subprocess.run(
                ["git", "clone", "--depth", "1", raw, tmpdir],
                capture_output=True, text=True, timeout=60, check=True
            )
        except subprocess.CalledProcessError as e:
            raise HTTPException(
                status_code=400,
                detail={"error": f"克隆仓库失败：{e.stderr.strip() if e.stderr else '无法访问该地址'}"},
            )
        except FileNotFoundError:
            raise HTTPException(
                status_code=500,
                detail={"error": "服务器未安装 Git，无法克隆远程仓库"},
            )
        CLONED_REPOS[raw] = tmpdir
        return tmpdir
    return raw

app = FastAPI(
    title="DevPulse API",
    description="开发者生产力与仓库健康度分析",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.detail if isinstance(exc.detail, dict) else {"error": str(exc.detail)},
        )
    return JSONResponse(
        status_code=500,
        content={"error": f"服务器内部错误：{str(exc)}"},
    )


@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "2.0.0",
        "timestamp": get_utc_timestamp(),
    }


@app.get("/api/stats")
async def get_repo_stats(repo_path: str = Query(".", description="Git 仓库路径或 GitHub URL")):
    repo_path = resolve_repo_path(repo_path)
    analyzer = GitAnalyzer(repo_path)
    if not analyzer.is_git_repo():
        raise HTTPException(
            status_code=400,
            detail={"error": "不是有效的 Git 仓库，请输入本地路径或完整的 GitHub 仓库地址"},
        )
    return analyzer.get_full_stats()


@app.get("/api/code")
async def get_code_stats(repo_path: str = Query(".", description="仓库路径")):
    repo_path = resolve_repo_path(repo_path)
    stats = CodeStats(repo_path)
    return stats.analyze()


@app.get("/api/contributors")
async def get_contributors(repo_path: str = Query(".", description="Git 仓库路径或 GitHub URL")):
    repo_path = resolve_repo_path(repo_path)
    analyzer = GitAnalyzer(repo_path)
    if not analyzer.is_git_repo():
        raise HTTPException(
            status_code=400,
            detail={"error": "不是有效的 Git 仓库，请输入本地路径或完整的 GitHub 仓库地址"},
        )
    return {
        "contributors": analyzer.get_contributors(),
        "commit_count": analyzer.get_commit_count(),
    }


@app.get("/api/activity")
async def get_activity(
    repo_path: str = Query(".", description="Git 仓库路径或 GitHub URL"),
    days: int = Query(90, ge=7, le=730, description="返回活跃度的天数（7-730）"),
):
    repo_path = resolve_repo_path(repo_path)
    analyzer = GitAnalyzer(repo_path)
    if not analyzer.is_git_repo():
        raise HTTPException(
            status_code=400,
            detail={"error": "不是有效的 Git 仓库，请输入本地路径或完整的 GitHub 仓库地址"},
        )
    return {"commit_activity": analyzer.get_commit_activity(days)}


@app.get("/api/churn")
async def get_churn(repo_path: str = Query(".", description="Git 仓库路径或 GitHub URL")):
    repo_path = resolve_repo_path(repo_path)
    analyzer = GitAnalyzer(repo_path)
    if not analyzer.is_git_repo():
        raise HTTPException(
            status_code=400,
            detail={"error": "不是有效的 Git 仓库，请输入本地路径或完整的 GitHub 仓库地址"},
        )
    return analyzer.get_code_churn()


@app.get("/api/branches")
async def get_branches(repo_path: str = Query(".", description="Git 仓库路径或 GitHub URL")):
    repo_path = resolve_repo_path(repo_path)
    analyzer = GitAnalyzer(repo_path)
    if not analyzer.is_git_repo():
        raise HTTPException(
            status_code=400,
            detail={"error": "不是有效的 Git 仓库，请输入本地路径或完整的 GitHub 仓库地址"},
        )
    return analyzer.get_branch_info()


@app.get("/")
async def serve_dashboard():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
