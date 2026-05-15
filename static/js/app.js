const CHART_COLORS = [
    '#58a6ff', '#3fb950', '#d29922', '#f85149', '#bc8cff',
    '#79c0ff', '#56d364', '#e3b341', '#ff7b72', '#d2a8ff',
    '#a5d6ff', '#7ee787', '#f0883e', '#ffa198', '#beabf7',
    '#39d353', '#9e6a03', '#da3633', '#8b949e', '#f2cc60',
];

let charts = {};

function destroyCharts() {
    Object.values(charts).forEach(c => c.destroy());
    charts = {};
}

function showLoading() {
    document.getElementById('loading-overlay').classList.remove('hidden');
    document.getElementById('status-text').textContent = '正在分析...';
    document.getElementById('status-indicator').className = 'indicator loading';
}

function hideLoading() {
    document.getElementById('loading-overlay').classList.add('hidden');
}

function showError(msg) {
    const toast = document.getElementById('error-toast');
    document.getElementById('error-message').textContent = msg;
    toast.classList.remove('hidden');
    document.getElementById('status-text').textContent = '分析出错';
    document.getElementById('status-indicator').className = 'indicator error';
    setTimeout(() => toast.classList.add('hidden'), 5000);
}

function setStatus(text, state) {
    document.getElementById('status-text').textContent = text;
    document.getElementById('status-indicator').className = 'indicator ' + state;
}

async function apiFetch(endpoint, params = {}) {
    const url = new URL(endpoint, window.location.origin);
    Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v));
    const resp = await fetch(url);
    if (!resp.ok) {
        let message = `请求失败 (HTTP ${resp.status})`;
        try {
            const body = await resp.json();
            message = body.detail?.error || body.error || body.detail || message;
        } catch (_) {}
        throw new Error(message);
    }
    return resp.json();
}

async function analyzeRepo() {
    const repoPath = document.getElementById('repo-path').value.trim() || '.';
    showLoading();
    destroyCharts();
    document.getElementById('dashboard').classList.add('hidden');
    document.getElementById('error-toast').classList.add('hidden');

    try {
        const [stats, codeStats] = await Promise.all([
            apiFetch('/api/stats', { repo_path: repoPath }),
            apiFetch('/api/code', { repo_path: repoPath }),
        ]);

        if (!stats.is_git_repo) {
            throw new Error('不是有效的 Git 仓库，请输入正确的仓库路径。');
        }

        renderDashboard(stats, codeStats);
        document.getElementById('dashboard').classList.remove('hidden');
        setStatus('分析完成', 'success');
    } catch (err) {
        showError(err.message);
        setStatus('分析失败', 'error');
    } finally {
        hideLoading();
    }
}

function renderDashboard(stats, codeStats) {
    renderOverview(stats, codeStats);
    renderActivityChart(stats.commit_activity);
    renderLanguageChart(codeStats.languages);
    renderContributorChart(stats.contributors);
    renderChurnChart(stats.code_churn.files.slice(0, 10));
    renderLanguageTable(codeStats.languages);
    renderChurnTable(stats.code_churn.files.slice(0, 50));
}

function renderOverview(stats, codeStats) {
    document.getElementById('commit-count').textContent = stats.commit_count;
    document.getElementById('contributor-count').textContent = stats.contributors.length;
    document.getElementById('file-count').textContent = codeStats.total_files;
    document.getElementById('code-lines').textContent = codeStats.total_code_lines.toLocaleString();
    document.getElementById('branch-count').textContent = stats.branch_info.branch_count;
}

function renderActivityChart(activity) {
    const ctx = document.getElementById('activity-chart').getContext('2d');
    const data = activity.filter((_, i) => i % 2 === 0);
    charts.activity = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.map(d => d.date.slice(5)),
            datasets: [{
                label: '提交次数',
                data: data.map(d => d.commits),
                backgroundColor: 'rgba(63, 185, 80, 0.6)',
                borderColor: '#3fb950',
                borderWidth: 1,
                borderRadius: 3,
                borderSkipped: false,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
            },
            scales: {
                x: {
                    ticks: { color: '#8b949e', maxTicksLimit: 15 },
                    grid: { color: 'rgba(48, 54, 61, 0.5)' },
                },
                y: {
                    ticks: { color: '#8b949e', stepSize: 1 },
                    grid: { color: 'rgba(48, 54, 61, 0.5)' },
                    beginAtZero: true,
                },
            },
        },
    });
}

function renderLanguageChart(languages) {
    const ctx = document.getElementById('language-chart').getContext('2d');
    const topLangs = languages.slice(0, 8);
    const otherPct = languages.slice(8).reduce((s, l) => s + l.percentage, 0);
    const labels = topLangs.map(l => l.language);
    const data = topLangs.map(l => l.code_lines);
    const colors = topLangs.map((_, i) => CHART_COLORS[i % CHART_COLORS.length]);

    if (otherPct > 0) {
        labels.push('其他');
        data.push(languages.slice(8).reduce((s, l) => s + l.code_lines, 0));
        colors.push('#8b949e');
    }

    charts.language = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels,
            datasets: [{
                data,
                backgroundColor: colors,
                borderColor: '#1c2129',
                borderWidth: 2,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        color: '#8b949e',
                        padding: 12,
                        font: { size: 12 },
                    },
                },
            },
        },
    });
}

function renderContributorChart(contributors) {
    const ctx = document.getElementById('contributor-chart').getContext('2d');
    const top = contributors.slice(0, 10);
    charts.contributor = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: top.map(c => c.name.length > 14 ? c.name.slice(0, 13) + '...' : c.name),
            datasets: [{
                label: '提交次数',
                data: top.map(c => c.commits),
                backgroundColor: CHART_COLORS.map(c => c + '99'),
                borderColor: CHART_COLORS,
                borderWidth: 1,
                borderRadius: 4,
                borderSkipped: false,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: 'y',
            plugins: {
                legend: { display: false },
            },
            scales: {
                x: {
                    ticks: { color: '#8b949e' },
                    grid: { color: 'rgba(48, 54, 61, 0.5)' },
                    beginAtZero: true,
                },
                y: {
                    ticks: { color: '#8b949e', font: { size: 11 } },
                    grid: { display: false },
                },
            },
        },
    });
}

function renderChurnChart(files) {
    const ctx = document.getElementById('churn-chart').getContext('2d');
    const shortNames = files.map(f => {
        const parts = f.filename.split('/');
        return parts.length > 2
            ? '.../' + parts.slice(-2).join('/')
            : f.filename;
    });
    charts.churn = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: shortNames,
            datasets: [
                {
                    label: '新增行数',
                    data: files.map(f => f.added),
                    backgroundColor: 'rgba(63, 185, 80, 0.6)',
                    borderColor: '#3fb950',
                    borderWidth: 1,
                    borderRadius: 3,
                    borderSkipped: false,
                },
                {
                    label: '删除行数',
                    data: files.map(f => f.deleted),
                    backgroundColor: 'rgba(248, 81, 73, 0.6)',
                    borderColor: '#f85149',
                    borderWidth: 1,
                    borderRadius: 3,
                    borderSkipped: false,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: { color: '#8b949e', usePointStyle: true, padding: 16 },
                },
            },
            scales: {
                x: {
                    stacked: true,
                    ticks: { color: '#8b949e', font: { size: 10 }, maxRotation: 45, minRotation: 0 },
                    grid: { display: false },
                },
                y: {
                    stacked: true,
                    ticks: { color: '#8b949e' },
                    grid: { color: 'rgba(48, 54, 61, 0.5)' },
                },
            },
        },
    });
}

const LANG_COLORS = {
    'Python': '#3572A5', 'JavaScript': '#f1e05a', 'TypeScript': '#3178c6',
    'HTML': '#e34c26', 'CSS': '#563d7c', 'Java': '#b07219',
    'Go': '#00ADD8', 'Rust': '#dea584', 'C++': '#f34b7d',
    'Ruby': '#701516', 'PHP': '#4F5D95', 'Shell': '#89e051',
    'Markdown': '#083fa1', 'JSON': '#292929', 'YAML': '#cb171e',
    'SQL': '#e38c00', 'Kotlin': '#A97BFF', 'Swift': '#F05138',
    'SCSS': '#c6538c', 'Dockerfile': '#384d54',
};

function getLangColor(language) {
    return LANG_COLORS[language] || '#8b949e';
}

function renderLanguageTable(languages) {
    const tbody = document.getElementById('language-table-body');
    const maxCodeLines = languages.length > 0 ? languages[0].code_lines : 1;
    tbody.innerHTML = languages.map(l => `
        <tr>
            <td>
                <span class="language-dot" style="background:${getLangColor(l.language)}"></span>
                ${l.language}
            </td>
            <td>${l.files}</td>
            <td>${l.code_lines.toLocaleString()}</td>
            <td>${l.blank_lines.toLocaleString()}</td>
            <td>
                <span class="share-bar" style="width:${Math.max(l.percentage, 2)}px;background:${getLangColor(l.language)}"></span>
                ${l.percentage}%
            </td>
        </tr>
    `).join('');
}

function renderChurnTable(files) {
    const tbody = document.getElementById('churn-table-body');
    tbody.innerHTML = files.map(f => `
        <tr>
            <td title="${f.filename}">${f.filename.length > 55 ? f.filename.slice(0, 53) + '...' : f.filename}</td>
            <td class="col-num added-text">+${f.added}</td>
            <td class="col-num deleted-text">-${f.deleted}</td>
            <td class="col-num">${f.net >= 0 ? '+' : ''}${f.net}</td>
            <td class="col-num">${f.commits}</td>
        </tr>
    `).join('');
}

document.getElementById('repo-path').addEventListener('keydown', function (e) {
    if (e.key === 'Enter') analyzeRepo();
});

window.addEventListener('load', function () {
    analyzeRepo();
});
