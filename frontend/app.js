/* ═══════════════════════════════════════════════════════════════════════
   MedAdvisor — Client-Side Application Logic
   ═══════════════════════════════════════════════════════════════════════ */

const API = '/api';

// ── DOM Elements ────────────────────────────────────────────────────────
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const uploadZone     = $('#uploadZone');
const fileInput      = $('#fileInput');
const uploadProgress = $('#uploadProgress');
const progressFill   = $('#progressFill');
const progressText   = $('#progressText');
const docList        = $('#docList');
const docCount       = $('#docCount');
const docEmpty       = $('#docEmpty');
const chatArea       = $('#chatArea');
const welcomeScreen  = $('#welcomeScreen');
const messagesContainer = $('#messagesContainer');
const queryInput     = $('#queryInput');
const sendBtn        = $('#sendBtn');
const statusDot      = $('#statusDot');
const statusText     = $('#statusText');
const sidebarToggle  = $('#sidebarToggle');
const sidebar        = $('#sidebar');

// ── State ───────────────────────────────────────────────────────────────
let isQuerying = false;
let documents  = [];

// ═══════════════════════════════════════════════════════════════════════
// UPLOAD LOGIC
// ═══════════════════════════════════════════════════════════════════════

uploadZone.addEventListener('click', () => fileInput.click());

uploadZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadZone.classList.add('drag-over');
});

uploadZone.addEventListener('dragleave', () => {
    uploadZone.classList.remove('drag-over');
});

uploadZone.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadZone.classList.remove('drag-over');
    const files = e.dataTransfer.files;
    if (files.length) uploadFiles(files);
});

fileInput.addEventListener('change', () => {
    if (fileInput.files.length) uploadFiles(fileInput.files);
    fileInput.value = '';
});

async function uploadFiles(files) {
    for (const file of files) {
        await uploadSingleFile(file);
    }
}

async function uploadSingleFile(file) {
    const ext = file.name.split('.').pop().toLowerCase();
    if (!['pdf', 'docx', 'txt'].includes(ext)) {
        showToast(`Unsupported file type: .${ext}`, 'error');
        return;
    }

    uploadProgress.style.display = 'block';
    progressFill.style.width = '20%';
    progressText.textContent = `Uploading ${file.name}...`;

    try {
        const form = new FormData();
        form.append('file', file);

        progressFill.style.width = '50%';
        progressText.textContent = `Processing ${file.name}...`;

        const res = await fetch(`${API}/upload`, { method: 'POST', body: form });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Upload failed');
        }

        progressFill.style.width = '100%';
        progressText.textContent = `✓ ${file.name} ingested successfully`;

        await loadDocuments();

        setTimeout(() => {
            uploadProgress.style.display = 'none';
            progressFill.style.width = '0%';
        }, 2000);

    } catch (err) {
        progressText.textContent = `✗ Error: ${err.message}`;
        progressFill.style.width = '0%';
        setTimeout(() => { uploadProgress.style.display = 'none'; }, 3000);
    }
}

// ═══════════════════════════════════════════════════════════════════════
// DOCUMENT LIBRARY
// ═══════════════════════════════════════════════════════════════════════

async function loadDocuments() {
    try {
        const res = await fetch(`${API}/documents`);
        const data = await res.json();
        documents = data.documents || [];
        renderDocumentList();
    } catch (err) {
        console.error('Failed to load documents:', err);
    }
}

function renderDocumentList() {
    docCount.textContent = documents.length;

    if (documents.length === 0) {
        docList.innerHTML = '';
        docList.appendChild(docEmpty);
        docEmpty.style.display = 'block';
        return;
    }

    docEmpty.style.display = 'none';
    docList.innerHTML = '';

    documents.forEach(doc => {
        const ext = doc.filename.split('.').pop().toLowerCase();
        const item = document.createElement('div');
        item.className = 'doc-item';
        item.innerHTML = `
            <div class="doc-icon ${ext}">${ext.toUpperCase()}</div>
            <div class="doc-info">
                <div class="doc-name" title="${doc.filename}">${doc.filename}</div>
                <div class="doc-meta">${doc.chunk_count} chunks · ${doc.page_count} pages</div>
            </div>
            <button class="doc-delete" onclick="deleteDoc('${doc.id}')" title="Delete document">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="3 6 5 6 21 6"/>
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                </svg>
            </button>
        `;
        docList.appendChild(item);
    });
}

async function deleteDoc(docId) {
    if (!confirm('Delete this document and all its chunks?')) return;

    try {
        const res = await fetch(`${API}/documents/${docId}`, { method: 'DELETE' });
        if (res.ok) {
            await loadDocuments();
        }
    } catch (err) {
        console.error('Delete failed:', err);
    }
}

// Make deleteDoc globally accessible for onclick
window.deleteDoc = deleteDoc;

// ═══════════════════════════════════════════════════════════════════════
// CHAT / QUERY LOGIC
// ═══════════════════════════════════════════════════════════════════════

queryInput.addEventListener('input', () => {
    sendBtn.disabled = !queryInput.value.trim() || isQuerying;
    // Auto-resize textarea
    queryInput.style.height = 'auto';
    queryInput.style.height = Math.min(queryInput.scrollHeight, 120) + 'px';
});

queryInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        if (!sendBtn.disabled) sendQuery();
    }
});

sendBtn.addEventListener('click', sendQuery);

async function sendQuery() {
    const question = queryInput.value.trim();
    if (!question || isQuerying) return;

    // Hide welcome, show messages
    if (welcomeScreen) welcomeScreen.style.display = 'none';

    // Add user message
    appendMessage('user', question);

    // Clear input
    queryInput.value = '';
    queryInput.style.height = 'auto';
    sendBtn.disabled = true;

    // Show loading
    isQuerying = true;
    setStatus('busy', 'Analyzing documents...');
    const loadingId = appendLoading();

    try {
        const res = await fetch(`${API}/query`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question }),
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Query failed');
        }

        const data = await res.json();
        removeLoading(loadingId);
        appendAssistantMessage(data);

    } catch (err) {
        removeLoading(loadingId);
        appendMessage('assistant', `⚠️ Error: ${err.message}`, true);
    } finally {
        isQuerying = false;
        setStatus('ready', 'Ready');
    }
}

// ═══════════════════════════════════════════════════════════════════════
// MESSAGE RENDERING
// ═══════════════════════════════════════════════════════════════════════

function appendMessage(role, text, isError = false) {
    const msg = document.createElement('div');
    msg.className = `message ${role}`;
    msg.innerHTML = `<div class="message-content${isError ? ' error' : ''}">${escapeHtml(text)}</div>`;
    messagesContainer.appendChild(msg);
    scrollToBottom();
}

function appendAssistantMessage(data) {
    const msg = document.createElement('div');
    msg.className = 'message assistant';

    let html = '<div class="message-content">';
    html += '<div class="message-label"><span class="dot"></span> MedAdvisor</div>';

    if (!data.has_answer) {
        // No answer — show explanation
        html += `
            <div class="no-answer">
                <div class="no-answer-icon">⚠️</div>
                <div class="no-answer-text">${escapeHtml(data.answer)}</div>
            </div>
        `;
    } else {
        // Reasoning steps
        if (data.reasoning_steps && data.reasoning_steps.length > 0) {
            html += '<div class="answer-section">';
            html += '<div class="answer-section-title">🧠 Reasoning</div>';
            html += '<ol class="reasoning-steps">';
            data.reasoning_steps.forEach(step => {
                html += `<li>${escapeHtml(step.replace(/^Step \d+:\s*/i, ''))}</li>`;
            });
            html += '</ol></div>';
        }

        // Main answer
        html += '<div class="answer-section">';
        html += '<div class="answer-section-title">💡 Answer</div>';
        html += `<div class="answer-text">${formatAnswer(data.answer)}</div>`;
        html += '</div>';

        // Citations
        if (data.citations && data.citations.length > 0) {
            html += '<div class="answer-section">';
            html += '<div class="answer-section-title">📋 Citations</div>';
            html += '<div class="citations-list">';
            data.citations.forEach(c => {
                html += `
                    <div class="citation-card">
                        <div class="citation-source">${escapeHtml(c.source || 'Unknown source')}</div>
                        <div class="citation-text">"${escapeHtml(c.relevant_text || '')}"</div>
                    </div>
                `;
            });
            html += '</div></div>';
        }
    }

    // Confidence badge
    if (data.confidence) {
        const level = data.confidence.toLowerCase();
        html += `<div class="confidence-badge ${level}">
            Confidence: ${data.confidence}${data.confidence_reason ? ' — ' + escapeHtml(data.confidence_reason) : ''}
        </div>`;
    }

    // Sources used
    if (data.sources_used && data.sources_used.length > 0) {
        html += '<div class="answer-section"><div class="answer-section-title">📎 Sources Retrieved</div>';
        html += '<div class="sources-used">';
        data.sources_used.forEach(s => {
            html += `<span class="source-pill" title="RRF Score: ${s.rrf_score}">${escapeHtml(s.source)}</span>`;
        });
        html += '</div></div>';
    }

    html += '</div>';
    msg.innerHTML = html;
    messagesContainer.appendChild(msg);
    scrollToBottom();
}

function appendLoading() {
    const id = 'loading-' + Date.now();
    const msg = document.createElement('div');
    msg.className = 'message assistant';
    msg.id = id;
    msg.innerHTML = `
        <div class="message-content">
            <div class="message-label"><span class="dot"></span> MedAdvisor</div>
            <div class="typing-indicator">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>
        </div>
    `;
    messagesContainer.appendChild(msg);
    scrollToBottom();
    return id;
}

function removeLoading(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

// ═══════════════════════════════════════════════════════════════════════
// UTILITIES
// ═══════════════════════════════════════════════════════════════════════

function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function formatAnswer(text) {
    if (!text) return '';
    // Convert [Source: ...] references to styled spans
    let html = escapeHtml(text);
    html = html.replace(
        /\[Source:\s*([^\]]+)\]/g,
        '<span class="source-pill">$1</span>'
    );
    // Convert newlines to paragraphs
    html = html.split('\n').filter(l => l.trim()).map(l => `<p>${l}</p>`).join('');
    return html;
}

function scrollToBottom() {
    chatArea.scrollTop = chatArea.scrollHeight;
}

function setStatus(state, text) {
    statusDot.className = `status-dot${state === 'busy' ? ' busy' : ''}`;
    statusText.textContent = text;
}

function showToast(message, type = 'info') {
    // Simple toast — could be enhanced
    console.log(`[${type}] ${message}`);
}

// ── Sidebar toggle (mobile) ────────────────────────────────────────────
sidebarToggle.addEventListener('click', () => {
    sidebar.classList.toggle('open');

    // Create/toggle overlay
    let overlay = document.querySelector('.sidebar-overlay');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.className = 'sidebar-overlay';
        overlay.addEventListener('click', () => {
            sidebar.classList.remove('open');
            overlay.classList.remove('visible');
        });
        document.body.appendChild(overlay);
    }
    overlay.classList.toggle('visible', sidebar.classList.contains('open'));
});

// ── Init ────────────────────────────────────────────────────────────────
loadDocuments();
