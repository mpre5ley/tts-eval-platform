// TTS Evaluation Platform - Main JavaScript

document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('synthesis-form');
    const loading = document.getElementById('loading');
    const results = document.getElementById('results');
    const submitBtn = document.getElementById('submit-btn');
    const textInput = document.getElementById('text-input');
    const charCountEl = document.getElementById('char-count');
    const wordCountEl = document.getElementById('word-count');
    
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
});
