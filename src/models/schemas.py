from pydantic import BaseModel
from typing import Optional


class Contributor(BaseModel):
    name: str
    email: str
    commits: int


class CommitActivityItem(BaseModel):
    date: str
    commits: int


class FileChurn(BaseModel):
    filename: str
    added: int
    deleted: int
    net: int
    commits: int


class CodeChurn(BaseModel):
    total_added: int
    total_deleted: int
    net_change: int
    files: list[FileChurn]


class BranchInfo(BaseModel):
    current_branch: str
    branch_count: int
    branches: list[str]


class FileTypeItem(BaseModel):
    extension: str
    count: int
    percentage: float


class LanguageStats(BaseModel):
    language: str
    files: int
    total_lines: int
    code_lines: int
    blank_lines: int
    percentage: float


class CodeStatsResponse(BaseModel):
    total_files: int
    total_lines: int
    total_code_lines: int
    total_blank_lines: int
    blank_percentage: float
    languages: list[LanguageStats]


class RepoStats(BaseModel):
    is_git_repo: bool
    repo_path: str
    commit_count: int
    contributors: list[Contributor]
    commit_activity: list[CommitActivityItem]
    code_churn: CodeChurn
    branch_info: BranchInfo
    file_types: list[FileTypeItem]


class ErrorResponse(BaseModel):
    error: str
    is_git_repo: bool


class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: str


class AnalyzeRequest(BaseModel):
    repo_path: Optional[str] = "."
