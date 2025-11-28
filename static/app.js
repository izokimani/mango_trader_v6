// MangoTrades V6 Dashboard JavaScript

let refreshInterval;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    loadAllData();
    setupEventListeners();
    
    // Auto-refresh every 30 seconds
    refreshInterval = setInterval(loadAllData, 30000);
});

function setupEventListeners() {
    document.getElementById('refreshBtn').addEventListener('click', loadAllData);
    
    const closeBtn = document.querySelector('.close');
    if (closeBtn) {
        closeBtn.addEventListener('click', () => {
            document.getElementById('modal').style.display = 'none';
        });
    }
    
    window.addEventListener('click', (e) => {
        const modal = document.getElementById('modal');
        if (e.target === modal) {
            modal.style.display = 'none';
        }
    });

    // Task runner (localhost only)
    const runTaskBtn = document.getElementById('runTaskBtn');
    if (runTaskBtn) {
        runTaskBtn.addEventListener('click', runTask);
    }
}

async function loadAllData() {
    try {
        await Promise.all([
            loadHealth(),
            loadMetrics(),
            loadTrackedCoins(),
            loadAnalysis(),
            loadLogs()
        ]);
        updateTimestamp();
    } catch (error) {
        console.error('Error loading data:', error);
    }
}

async function loadHealth() {
    try {
        const response = await fetch('/api/health');
        const data = await response.json();
        
        const container = document.getElementById('healthStatus');
        container.innerHTML = `
            <div class="health-item ${data.status === 'healthy' ? 'healthy' : 'degraded'}">
                <strong>Status:</strong> ${data.status.toUpperCase()}
            </div>
            <div class="health-item ${data.trade_count > 0 ? 'healthy' : 'info'}">
                <strong>Trades:</strong> ${data.trade_count}
            </div>
            <div class="health-item ${data.log_files > 0 ? 'healthy' : 'info'}">
                <strong>Log Files:</strong> ${data.log_files}
            </div>
            <div class="health-item ${data.analysis_files > 0 ? 'healthy' : 'info'}">
                <strong>Analysis Reports:</strong> ${data.analysis_files}
            </div>
        `;
        
        if (data.issues && data.issues.length > 0) {
            container.innerHTML += `
                <div class="health-item error" style="width: 100%; margin-top: 10px;">
                    <strong>Issues:</strong><br>
                    ${data.issues.map(issue => `• ${issue}`).join('<br>')}
                </div>
            `;
        }
    } catch (error) {
        document.getElementById('healthStatus').innerHTML = 
            `<div class="health-item error">Error loading health status: ${error.message}</div>`;
    }
}

async function loadMetrics() {
    try {
        const response = await fetch('/api/metrics');
        const data = await response.json();
        
        // Display metrics
        const overall = data.overall;
        const metricsContainer = document.getElementById('metrics');
        
        metricsContainer.innerHTML = `
            <div class="metric-card">
                <h3>Total Trades</h3>
                <div class="value">${overall.total_trades || 0}</div>
            </div>
            <div class="metric-card">
                <h3>Avg Return</h3>
                <div class="value">${formatPercent(overall.avg_return)}</div>
            </div>
            <div class="metric-card">
                <h3>Win Rate</h3>
                <div class="value">${formatPercent(overall.win_rate)}</div>
            </div>
            <div class="metric-card">
                <h3>Avg Rank</h3>
                <div class="value">${overall.avg_rank ? overall.avg_rank.toFixed(1) : 'N/A'}</div>
                <div class="label">out of 16</div>
            </div>
            <div class="metric-card">
                <h3>Best Return</h3>
                <div class="value">${formatPercent(overall.best_return)}</div>
            </div>
            <div class="metric-card">
                <h3>Worst Return</h3>
                <div class="value">${formatPercent(overall.worst_return)}</div>
            </div>
            <div class="metric-card">
                <h3>Model Version</h3>
                <div class="value">v${overall.current_version || 1}</div>
            </div>
        `;
        
        // Display recent trades
        displayTrades(data.recent_trades, 'recentTrades');
        
        // Display pending trades
        if (data.pending_trades && data.pending_trades.length > 0) {
            document.getElementById('pendingSection').style.display = 'block';
            displayPendingTrades(data.pending_trades, 'pendingTrades');
        } else {
            document.getElementById('pendingSection').style.display = 'none';
        }
        
        // Display model history
        displayModelHistory(data.model_history, 'modelHistory');
        
    } catch (error) {
        document.getElementById('metrics').innerHTML = 
            `<div class="error">Error loading metrics: ${error.message}</div>`;
    }
}

function displayTrades(trades, containerId) {
    const container = document.getElementById(containerId);
    
    if (!trades || trades.length === 0) {
        container.innerHTML = '<p>No crypto trades recorded yet. The bot runs daily at 23:55 UTC.</p>';
        return;
    }
    
    container.innerHTML = `
        <table>
            <thead>
                <tr>
                    <th>Date</th>
                    <th>Coin</th>
                    <th>Score</th>
                    <th>Return</th>
                    <th>Rank</th>
                    <th>Model</th>
                </tr>
            </thead>
            <tbody>
                ${trades.map(trade => `
                    <tr>
                        <td>${trade.date}</td>
                        <td><strong>${trade.chosen_coin}</strong></td>
                        <td>${trade.chosen_score ? trade.chosen_score.toFixed(4) : 'N/A'}</td>
                        <td>
                            <span class="badge ${trade.actual_24h_return_of_chosen >= 0 ? 'success' : 'danger'}">
                                ${formatPercent(trade.actual_24h_return_of_chosen)}
                            </span>
                        </td>
                        <td>#${trade.rank_of_chosen || 'N/A'}</td>
                        <td>v${trade.model_version || 1}</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
}

function displayPendingTrades(trades, containerId) {
    const container = document.getElementById(containerId);
    
    container.innerHTML = `
        <table>
            <thead>
                <tr>
                    <th>Date</th>
                    <th>Coin</th>
                    <th>Score</th>
                    <th>Model</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
                ${trades.map(trade => `
                    <tr>
                        <td>${trade.date}</td>
                        <td><strong>${trade.chosen_coin}</strong></td>
                        <td>${trade.chosen_score ? trade.chosen_score.toFixed(4) : 'N/A'}</td>
                        <td>v${trade.model_version || 1}</td>
                        <td><span class="badge warning">Pending</span></td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
}

function displayModelHistory(history, containerId) {
    const container = document.getElementById(containerId);
    
        if (!history || history.length === 0) {
            container.innerHTML = '<p>No model upgrades yet. The bot will automatically improve its scoring function when it finds better strategies.</p>';
            return;
        }
    
    container.innerHTML = `
        <table>
            <thead>
                <tr>
                    <th>Date</th>
                    <th>Version</th>
                    <th>Improvement</th>
                    <th>Spearman Correlation</th>
                    <th>Avg Daily Return</th>
                </tr>
            </thead>
            <tbody>
                ${history.map(model => `
                    <tr>
                        <td>${model.date}</td>
                        <td><strong>v${model.version}</strong></td>
                        <td><span class="badge info">${model.improvement_type || 'N/A'}</span></td>
                        <td>${model.spearman_correlation ? model.spearman_correlation.toFixed(3) : 'N/A'}</td>
                        <td>${formatPercent(model.avg_daily_return)}</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
}

async function loadAnalysis() {
    try {
        const response = await fetch('/api/analysis');
        const data = await response.json();
        
        const container = document.getElementById('analysisReports');
        
        if (!data.reports || data.reports.length === 0) {
            container.innerHTML = '<p>No analysis reports available yet. Reports are generated daily after trades complete.</p>';
            return;
        }
        
        container.innerHTML = data.reports.map(report => `
            <div class="report-item" onclick="viewAnalysis('${report.file}')">
                <h3>Analysis Report - ${report.date || 'Unknown Date'}</h3>
                <div class="meta">
                    Errors: ${report.errors_count || 0} | 
                    Warnings: ${report.warnings_count || 0}
                </div>
            </div>
        `).join('');
        
    } catch (error) {
        document.getElementById('analysisReports').innerHTML = 
            `<div class="error">Error loading analysis: ${error.message}</div>`;
    }
}

async function viewAnalysis(filename) {
    try {
        const response = await fetch(`/api/analysis/${filename}`);
        const data = await response.json();
        
        const modal = document.getElementById('modal');
        const modalBody = document.getElementById('modalBody');
        
        modalBody.innerHTML = `
            <h2>Analysis Report - ${data.date}</h2>
            <h3>Metrics</h3>
            <pre>${JSON.stringify(data.metrics, null, 2)}</pre>
            ${data.errors && data.errors.length > 0 ? `
                <h3>Errors</h3>
                <pre>${JSON.stringify(data.errors, null, 2)}</pre>
            ` : ''}
            ${data.warnings && data.warnings.length > 0 ? `
                <h3>Warnings</h3>
                <pre>${JSON.stringify(data.warnings, null, 2)}</pre>
            ` : ''}
        `;
        
        modal.style.display = 'block';
    } catch (error) {
        alert('Error loading analysis: ' + error.message);
    }
}

async function loadLogs() {
    try {
        const response = await fetch('/api/logs');
        const data = await response.json();
        
        const container = document.getElementById('logsViewer');
        
        if (!data.logs || data.logs.length === 0) {
            container.innerHTML = '<p>No logs available.</p>';
            return;
        }
        
        let logsHtml = '';
        data.logs.forEach(log => {
            if (log.error) {
                logsHtml += `<div class="log-entry error">Error loading ${log.date}: ${log.error}</div>`;
            } else {
                const lines = log.content.split('\n');
                lines.forEach(line => {
                    if (!line.trim()) return;
                    let className = 'info';
                    if (line.includes('ERROR')) className = 'error';
                    else if (line.includes('WARNING')) className = 'warning';
                    logsHtml += `<div class="log-entry ${className}">${escapeHtml(line)}</div>`;
                });
            }
        });
        
        container.innerHTML = logsHtml;
        
        // Auto-scroll to bottom
        container.scrollTop = container.scrollHeight;
        
    } catch (error) {
        document.getElementById('logsViewer').innerHTML = 
            `<div class="error">Error loading logs: ${error.message}</div>`;
    }
}

async function runTask() {
    const taskSelect = document.getElementById('taskSelect');
    const taskOutput = document.getElementById('taskOutput');
    const runBtn = document.getElementById('runTaskBtn');
    
    const task = taskSelect.value;
    
    runBtn.disabled = true;
    runBtn.textContent = 'Running...';
    taskOutput.classList.add('show');
    taskOutput.textContent = `Running task: ${task}\n\n`;
    
    try {
        const response = await fetch('/api/run-task', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ task })
        });
        
        const data = await response.json();
        
        if (data.success) {
            taskOutput.textContent += `\n=== STDOUT ===\n${data.stdout}\n\n=== STDERR ===\n${data.stderr}`;
            taskOutput.style.color = '#155724';
        } else {
            taskOutput.textContent += `\nError: ${data.error || 'Task failed'}\n\n=== STDOUT ===\n${data.stdout}\n\n=== STDERR ===\n${data.stderr}`;
            taskOutput.style.color = '#721c24';
        }
        
        // Refresh data after task completes
        setTimeout(loadAllData, 2000);
        
    } catch (error) {
        taskOutput.textContent += `\nError: ${error.message}`;
        taskOutput.style.color = '#721c24';
    } finally {
        runBtn.disabled = false;
        runBtn.textContent = 'Run Task';
    }
}

function formatPercent(value) {
    if (value === null || value === undefined) return 'N/A';
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

async function loadTrackedCoins() {
    try {
        const coins = [
            'BTCUSD', 'ETHUSD', 'SOLUSD', 'ADAUSD', 'DOGEUSD', 'AVAXUSD',
            'LINKUSD', 'MATICUSD', 'DOTUSD', 'LTCUSD', 'BCHUSD', 'XLMUSD',
            'ALGOUSD', 'UNIUSD', 'AAVEUSD', 'MKRUSD'
        ];
        
        const container = document.getElementById('trackedCoins');
        container.innerHTML = coins.map(coin => {
            const symbol = coin.replace('USD', '');
            return `
                <div class="coin-badge">
                    <strong>${symbol}</strong>
                    <span class="coin-pair">${coin}</span>
                </div>
            `;
        }).join('');
    } catch (error) {
        document.getElementById('trackedCoins').innerHTML = 
            `<div class="error">Error loading coins: ${error.message}</div>`;
    }
}

function updateTimestamp() {
    const now = new Date();
    document.getElementById('lastUpdate').textContent = 
        `Last updated: ${now.toLocaleTimeString()}`;
}

