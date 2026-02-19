// TTS Evaluation Platform - Main JavaScript

document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('synthesis-form');
    const loading = document.getElementById('loading');
    const results = document.getElementById('results');
    const submitBtn = document.getElementById('submit-btn');
    const textInput = document.getElementById('text-input');
    const charCountEl = document.getElementById('char-count');
    const wordCountEl = document.getElementById('word-count');
    
    // Tab navigation
    const tabBtns = document.querySelectorAll('.tab-btn');
    tabBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const tabId = this.dataset.tab;
            
            // Update active tab button
            tabBtns.forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            
            // Show/hide tab content
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.add('hidden');
            });
            document.getElementById(`${tabId}-tab`).classList.remove('hidden');
        });
    });
    
    // Character and word counter
    if (textInput && charCountEl && wordCountEl) {
        textInput.addEventListener('input', function() {
            const text = this.value;
            charCountEl.textContent = text.length;
            wordCountEl.textContent = text.trim() ? text.trim().split(/\s+/).length : 0;
        });
    }
    
    // Provider card selection highlighting
    document.querySelectorAll('.provider-card input[type="checkbox"]').forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            const card = this.closest('.provider-card');
            if (this.checked) {
                card.classList.add('selected');
            } else {
                card.classList.remove('selected');
            }
            
            // Limit to 5 providers
            const checkedCount = document.querySelectorAll('.provider-card input[type="checkbox"]:checked').length;
            if (checkedCount >= 5) {
                document.querySelectorAll('.provider-card input[type="checkbox"]:not(:checked)').forEach(cb => {
                    cb.disabled = true;
                    cb.closest('.provider-card').style.opacity = '0.5';
                });
            } else {
                document.querySelectorAll('.provider-card input[type="checkbox"]').forEach(cb => {
                    cb.disabled = false;
                    cb.closest('.provider-card').style.opacity = '1';
                });
            }
        });
    });
    
    // Form submission
    if (form) {
        form.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const text = textInput.value.trim();
            if (!text) {
                alert('Please enter text to synthesize');
                return;
            }
            
            // Get selected providers and their voices
            const providers = [];
            document.querySelectorAll('.provider-card input[type="checkbox"]:checked').forEach(checkbox => {
                const card = checkbox.closest('.provider-card');
                const providerId = checkbox.value;
                const voiceSelect = card.querySelector('.voice-select');
                const voiceId = voiceSelect ? voiceSelect.value : '';
                
                providers.push({
                    provider_id: providerId,
                    voice_id: voiceId,
                    options: {}
                });
            });
            
            if (providers.length === 0) {
                alert('Please select at least one TTS provider');
                return;
            }
            
            const streaming = true;  // Always use streaming mode for jitter/RTF measurement
            const sessionName = document.getElementById('session-name')?.value || '';
            
            // Show loading state
            loading.classList.remove('hidden');
            results.classList.add('hidden');
            submitBtn.disabled = true;
            submitBtn.querySelector('.btn-text').classList.add('hidden');
            submitBtn.querySelector('.btn-loading').classList.remove('hidden');
            
            try {
                const response = await fetch('/api/synthesize/batch/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        text: text,
                        providers: providers,
                        streaming: streaming,
                        session_name: sessionName
                    })
                });
                
                const data = await response.json();
                
                if (data.error) {
                    showError(data.error);
                    return;
                }
                
                displayResults(data);
                
            } catch (error) {
                showError('Connection error: ' + error.message);
            } finally {
                loading.classList.add('hidden');
                submitBtn.disabled = false;
                submitBtn.querySelector('.btn-text').classList.remove('hidden');
                submitBtn.querySelector('.btn-loading').classList.add('hidden');
            }
        });
    }
    
    function displayResults(data) {
        results.classList.remove('hidden');
        
        // Session ID
        document.getElementById('session-id').textContent = data.session_id;
        
        // Metrics summary
        const summaryGrid = document.getElementById('metrics-summary');
        const successfulResults = data.results.filter(r => r.success);
        
        if (successfulResults.length > 0) {
            const avgTTFA = average(successfulResults.map(r => r.metrics.time_to_first_audio));
            const avgTotal = average(successfulResults.map(r => r.metrics.total_synthesis_time));
            const avgJitter = average(successfulResults.filter(r => r.metrics.playback_jitter).map(r => r.metrics.playback_jitter));
            const fastestProvider = successfulResults.reduce((a, b) => 
                (a.metrics.total_synthesis_time || Infinity) < (b.metrics.total_synthesis_time || Infinity) ? a : b
            );
            
            summaryGrid.innerHTML = `
                <div class="metric-card">
                    <div class="metric-label">Avg Time to First Audio</div>
                    <div class="metric-value">${avgTTFA.toFixed(1)}<span class="metric-unit">ms</span></div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Avg Total Latency</div>
                    <div class="metric-value">${avgTotal.toFixed(1)}<span class="metric-unit">ms</span></div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Avg Playback Jitter</div>
                    <div class="metric-value">${avgJitter ? avgJitter.toFixed(2) : '-'}<span class="metric-unit">ms</span></div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Fastest Provider</div>
                    <div class="metric-value" style="font-size: 1.2rem;">${fastestProvider.provider_name}</div>
                </div>
            `;
        } else {
            summaryGrid.innerHTML = '<p class="error-message">No successful synthesis results</p>';
        }
        
        // Comparison chart
        const chartContainer = document.getElementById('comparison-chart');
        const maxTime = Math.max(...data.results.map(r => r.metrics.total_synthesis_time || 0));
        
        chartContainer.innerHTML = data.results.map(result => {
            const ttfaWidth = ((result.metrics.time_to_first_audio || 0) / maxTime * 100);
            const totalWidth = ((result.metrics.total_synthesis_time || 0) / maxTime * 100);
            
            return `
                <div class="chart-row">
                    <span class="chart-label">${result.provider_name}</span>
                    <div class="chart-bars">
                        <div class="bar ttfa" style="width: ${ttfaWidth}%" 
                             title="TTFA: ${result.metrics.time_to_first_audio?.toFixed(1) || '-'}ms"></div>
                        <div class="bar total" style="width: ${totalWidth}%" 
                             title="Total: ${result.metrics.total_synthesis_time?.toFixed(1) || '-'}ms"></div>
                    </div>
                    <span class="chart-value">${result.metrics.total_synthesis_time?.toFixed(0) || '-'}ms</span>
                </div>
            `;
        }).join('');
        
        // Individual result cards
        const resultsGrid = document.getElementById('results-cards');
        resultsGrid.innerHTML = data.results.map(result => createResultCard(result)).join('');
        
        // Scroll to results
        results.scrollIntoView({ behavior: 'smooth' });
    }
    
    function createResultCard(result) {
        const statusClass = result.success ? 'success' : 'error';
        const metrics = result.metrics;
        
        let audioSection = '';
        if (result.success && result.audio_base64) {
            audioSection = `
                <div class="audio-player">
                    <div class="audio-player-label">Audio Playback</div>
                    <audio controls data-evaluation-id="${result.evaluation_id || ''}"
                           src="data:audio/${metrics.audio_format || 'mp3'};base64,${result.audio_base64}">
                        Your browser does not support the audio element.
                    </audio>
                </div>
            `;
        }
        
        let errorSection = '';
        if (!result.success && result.error_message) {
            errorSection = `
                <div class="error-message" style="margin-top: 15px;">
                    <strong>Error:</strong> ${escapeHtml(result.error_message)}
                </div>
            `;
        }
        
        return `
            <div class="result-card ${statusClass}">
                <div class="result-header">
                    <span class="result-provider">${escapeHtml(result.provider_name)}</span>
                    <span class="result-status ${statusClass}">${result.success ? 'Success' : 'Failed'}</span>
                </div>
                <div class="result-voice">Voice: ${escapeHtml(result.voice_id)} ${result.model_id ? `| Model: ${escapeHtml(result.model_id)}` : ''}</div>
                
                <div class="result-metrics">
                    <div class="result-metric">
                        <div class="result-metric-label">Time to First Byte</div>
                        <div class="result-metric-value">${metrics.time_to_first_byte?.toFixed(1) || '-'} ms</div>
                    </div>
                    <div class="result-metric">
                        <div class="result-metric-label">Time to First Audio</div>
                        <div class="result-metric-value">${metrics.time_to_first_audio?.toFixed(1) || '-'} ms</div>
                    </div>
                    <div class="result-metric">
                        <div class="result-metric-label">Total Latency</div>
                        <div class="result-metric-value">${metrics.total_synthesis_time?.toFixed(1) || '-'} ms</div>
                    </div>
                    <div class="result-metric">
                        <div class="result-metric-label">Real-time Factor</div>
                        <div class="result-metric-value">${metrics.realtime_factor?.toFixed(2) || '-'}x</div>
                    </div>
                    <div class="result-metric">
                        <div class="result-metric-label">Audio Duration</div>
                        <div class="result-metric-value">${metrics.audio_duration?.toFixed(2) || '-'} s</div>
                    </div>
                    <div class="result-metric">
                        <div class="result-metric-label">Audio Size</div>
                        <div class="result-metric-value">${formatBytes(metrics.audio_size)}</div>
                    </div>
                    ${metrics.is_streaming ? `
                    <div class="result-metric">
                        <div class="result-metric-label">Chunk Jitter</div>
                        <div class="result-metric-value">${metrics.playback_jitter?.toFixed(2) || '-'} ms</div>
                    </div>
                    <div class="result-metric">
                        <div class="result-metric-label">Avg Chunk Size</div>
                        <div class="result-metric-value">${formatBytes(metrics.avg_chunk_size)}</div>
                    </div>
                    ` : ''}
                </div>
                
                ${audioSection}
                ${errorSection}
            </div>
        `;
    }
    
    function showError(message) {
        const resultsGrid = document.getElementById('results-cards');
        const summaryGrid = document.getElementById('metrics-summary');
        
        results.classList.remove('hidden');
        summaryGrid.innerHTML = '';
        resultsGrid.innerHTML = `
            <div class="result-card error">
                <div class="result-header">
                    <span class="result-provider">Error</span>
                    <span class="result-status error">Failed</span>
                </div>
                <div class="error-message">${escapeHtml(message)}</div>
            </div>
        `;
    }
    
    function average(arr) {
        if (!arr || arr.length === 0) return 0;
        const validNumbers = arr.filter(n => n != null && !isNaN(n));
        if (validNumbers.length === 0) return 0;
        return validNumbers.reduce((a, b) => a + b, 0) / validNumbers.length;
    }
    
    function formatBytes(bytes) {
        if (bytes == null) return '-';
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    }
    
    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    // ========== Batch CSV Upload ==========
    
    const csvFileInput = document.getElementById('csv-file-input');
    const csvDropZone = document.getElementById('csv-drop-zone');
    const startBatchBtn = document.getElementById('start-batch-btn');
    const selectedFileName = document.getElementById('selected-file-name');
    const batchProgress = document.getElementById('batch-progress');
    
    let batchTasks = [];
    let selectedFile = null;
    
    // File input change
    if (csvFileInput) {
        csvFileInput.addEventListener('change', function(e) {
            if (e.target.files.length > 0) {
                handleFileSelection(e.target.files[0]);
            }
        });
    }
    
    // Drag and drop
    if (csvDropZone) {
        csvDropZone.addEventListener('click', () => csvFileInput?.click());
        
        csvDropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            csvDropZone.classList.add('dragover');
        });
        
        csvDropZone.addEventListener('dragleave', () => {
            csvDropZone.classList.remove('dragover');
        });
        
        csvDropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            csvDropZone.classList.remove('dragover');
            
            if (e.dataTransfer.files.length > 0) {
                const file = e.dataTransfer.files[0];
                if (file.name.endsWith('.csv')) {
                    handleFileSelection(file);
                } else {
                    alert('Please upload a CSV file');
                }
            }
        });
    }
    
    function handleFileSelection(file) {
        selectedFile = file;
        selectedFileName.textContent = `Selected: ${file.name}`;
        selectedFileName.classList.remove('hidden');
        updateBatchButtonState();
    }
    
    // Update batch button state based on file and provider selection
    function updateBatchButtonState() {
        const selectedProviders = document.querySelectorAll('input[name="batch_provider"]:checked');
        startBatchBtn.disabled = !(selectedFile && selectedProviders.length > 0);
    }
    
    // Listen for batch provider checkbox changes - highlight card and update button state
    document.querySelectorAll('.batch-provider-card input[name="batch_provider"]').forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            const card = this.closest('.batch-provider-card');
            if (this.checked) {
                card.classList.add('selected');
            } else {
                card.classList.remove('selected');
            }
            updateBatchButtonState();
        });
    });
    
    // Start batch button
    if (startBatchBtn) {
        startBatchBtn.addEventListener('click', async () => {
            if (!selectedFile) return;
            
            // Get selected providers with their voice selections
            const providerVoices = {};
            document.querySelectorAll('.batch-provider-card input[name="batch_provider"]:checked').forEach(checkbox => {
                const card = checkbox.closest('.batch-provider-card');
                const providerId = checkbox.value;
                const voiceSelect = card.querySelector('.batch-voice-select');
                const voiceId = voiceSelect ? voiceSelect.value : '';
                providerVoices[providerId] = voiceId;
            });
            
            const selectedProviders = Object.keys(providerVoices);
            
            if (selectedProviders.length === 0) {
                alert('Please select at least one TTS provider');
                return;
            }
            
            // Get session name
            const sessionName = document.getElementById('batch-session-name').value.trim();
            
            // Upload and parse CSV with providers, voices and session name
            const formData = new FormData();
            formData.append('file', selectedFile);
            formData.append('providers', selectedProviders.join(','));
            formData.append('provider_voices', JSON.stringify(providerVoices));
            formData.append('session_name', sessionName);
            
            startBatchBtn.disabled = true;
            startBatchBtn.querySelector('.btn-text').classList.add('hidden');
            startBatchBtn.querySelector('.btn-loading').classList.remove('hidden');
            
            try {
                const response = await fetch('/api/batch/upload/', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                
                if (data.error) {
                    alert('Error: ' + data.error);
                    resetBatchUI();
                    return;
                }
                
                batchTasks = data.tasks;
                executeBatchTasks(batchTasks);
                
            } catch (error) {
                alert('Error uploading CSV: ' + error.message);
                resetBatchUI();
            }
        });
    }
    
    async function executeBatchTasks(tasks) {
        // Show progress section
        batchProgress.classList.remove('hidden');
        
        const progressBar = document.getElementById('batch-progress-bar');
        const progressCount = document.getElementById('progress-count');
        const elapsedTime = document.getElementById('elapsed-time');
        const successCount = document.getElementById('success-count');
        const failedCount = document.getElementById('failed-count');
        const currentTaskText = document.getElementById('current-task-text');
        const logEntries = document.getElementById('log-entries');
        
        // Reset counters
        let completed = 0;
        let success = 0;
        let failed = 0;
        const total = tasks.length;
        const startTime = Date.now();
        
        // Update elapsed time every second
        const timerInterval = setInterval(() => {
            const elapsed = Math.floor((Date.now() - startTime) / 1000);
            const minutes = Math.floor(elapsed / 60).toString().padStart(2, '0');
            const seconds = (elapsed % 60).toString().padStart(2, '0');
            elapsedTime.textContent = `${minutes}:${seconds}`;
        }, 1000);
        
        progressCount.textContent = `0 / ${total}`;
        logEntries.innerHTML = '';
        
        // Execute tasks sequentially
        for (let i = 0; i < tasks.length; i++) {
            const task = tasks[i];
            currentTaskText.textContent = `${task.provider}: "${task.prompt.substring(0, 50)}${task.prompt.length > 50 ? '...' : ''}"`;
            
            try {
                const response = await fetch('/api/batch/execute/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        prompt: task.prompt,
                        provider: task.provider,
                        voice_id: task.voice_id,
                        session_name: task.session_name
                    })
                });
                
                const result = await response.json();
                
                completed++;
                if (result.success) {
                    success++;
                    addLogEntry(logEntries, task, result, true);
                } else {
                    failed++;
                    addLogEntry(logEntries, task, result, false);
                }
                
            } catch (error) {
                completed++;
                failed++;
                addLogEntry(logEntries, task, { error_message: error.message }, false);
            }
            
            // Update progress
            const percent = (completed / total) * 100;
            progressBar.style.width = `${percent}%`;
            progressBar.textContent = `${Math.round(percent)}%`;
            progressCount.textContent = `${completed} / ${total}`;
            successCount.textContent = success;
            failedCount.textContent = failed;
        }
        
        // Complete
        clearInterval(timerInterval);
        currentTaskText.textContent = `Batch complete! ${success} succeeded, ${failed} failed.`;
        resetBatchUI();
    }
    
    function addLogEntry(container, task, result, isSuccess) {
        const entry = document.createElement('div');
        entry.className = `log-entry ${isSuccess ? 'success' : 'error'}`;
        
        const metrics = result.metrics || {};
        const metricsHtml = isSuccess ? `
            <div class="log-metrics">
                <div class="log-metric">Latency: <span>${metrics.total_synthesis_time?.toFixed(0) || '-'}ms</span></div>
                <div class="log-metric">RTF: <span>${metrics.realtime_factor?.toFixed(2) || '-'}x</span></div>
            </div>
        ` : `<div class="log-metric error-text">${escapeHtml(result.error_message || 'Failed')}</div>`;
        
        entry.innerHTML = `
            <div>
                <span class="log-provider">${escapeHtml(task.provider)}</span>
                <span class="log-prompt">${escapeHtml(task.prompt.substring(0, 40))}${task.prompt.length > 40 ? '...' : ''}</span>
            </div>
            ${metricsHtml}
        `;
        
        container.insertBefore(entry, container.firstChild);
    }
    
    function resetBatchUI() {
        startBatchBtn.disabled = false;
        startBatchBtn.querySelector('.btn-text').classList.remove('hidden');
        startBatchBtn.querySelector('.btn-loading').classList.add('hidden');
    }
});

// Download sample CSV
function downloadSampleCSV() {
    const csvContent = `Hello, how are you today?
The quick brown fox jumps over the lazy dog.
Welcome to our platform.
Please leave a message after the beep.
Your order has been confirmed and will arrive tomorrow.
Press 1 for sales, press 2 for support.
Thank you for calling. Have a great day!
The weather today is sunny with a high of 75 degrees.`;
    
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'sample_prompts.csv';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
}
