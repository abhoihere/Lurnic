# src/lurnic/api.py
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse
import time

from .core import process_pdf, ask_gemini_direct
from .config import Config

app = FastAPI(title="Lurnic API")

# HTML with Markdown rendering
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Lurnic — Study Smarter</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif; background: #f9fafb; height: 100vh; overflow: hidden; }
        .app { display: flex; height: 100vh; width: 100%; }
        
        /* Sidebar */
        .sidebar { width: 280px; background: #fff; border-right: 1px solid #e5e7eb; display: flex; flex-direction: column; padding: 2rem 1.5rem; gap: 2rem; overflow-y: auto; }
        .logo { display: flex; align-items: center; gap: 10px; margin-bottom: 0.5rem; }
        .logo-icon { font-size: 28px; }
        .logo-text { font-size: 1.5rem; font-weight: 600; background: linear-gradient(135deg, #3b82f6, #8b5cf6); -webkit-background-clip: text; background-clip: text; color: transparent; }
        .tagline { font-size: 0.8rem; color: #6b7280; margin-top: -0.5rem; margin-bottom: 0.5rem; }
        .nav-section { display: flex; flex-direction: column; gap: 0.5rem; }
        .nav-title { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.05em; color: #9ca3af; font-weight: 600; margin-bottom: 0.5rem; }
        .mode-card, .tier-card { background: #f3f4f6; border-radius: 12px; padding: 1rem; cursor: pointer; transition: all 0.2s ease; border: 2px solid transparent; margin-bottom: 0.75rem; }
        .mode-card.selected, .tier-card.selected { background: #eff6ff; border-color: #3b82f6; }
        .mode-card:hover, .tier-card:hover { background: #eef2ff; }
        .mode-name, .tier-name { font-weight: 600; font-size: 0.9rem; margin-bottom: 0.25rem; }
        .mode-desc, .tier-desc { font-size: 0.7rem; color: #6b7280; }
        .badge { display: inline-block; font-size: 0.6rem; padding: 2px 8px; border-radius: 20px; margin-top: 0.5rem; }
        .badge-free { background: #e5e7eb; color: #374151; }
        .badge-paid { background: #3b82f6; color: white; }
        .info-box { background: #f9fafb; border-radius: 12px; padding: 1rem; margin-top: auto; font-size: 0.75rem; color: #6b7280; border: 1px solid #e5e7eb; }
        
        /* Main content */
        .main-content { flex: 1; overflow-y: auto; padding: 2rem; }
        .upload-card { background: white; border-radius: 24px; border: 1px solid #e5e7eb; padding: 2rem; margin-bottom: 1.5rem; display: none; }
        .upload-card.visible { display: block; }
        .upload-area { border: 2px dashed #e5e7eb; border-radius: 16px; padding: 2rem; text-align: center; cursor: pointer; }
        .upload-area:hover { border-color: #3b82f6; background: #fafcff; }
        .file-name { margin-top: 0.5rem; font-size: 0.8rem; color: #3b82f6; display: none; }
        .question-area { margin-top: 1.5rem; }
        label { font-size: 0.85rem; font-weight: 500; color: #374151; display: block; margin-bottom: 0.5rem; }
        textarea { width: 100%; padding: 0.75rem 1rem; border: 1px solid #e5e7eb; border-radius: 12px; font-size: 0.95rem; font-family: inherit; resize: vertical; }
        textarea:focus { outline: none; border-color: #3b82f6; box-shadow: 0 0 0 3px rgba(59,130,246,0.1); }
        button { background: #3b82f6; color: white; border: none; padding: 0.75rem 1.5rem; border-radius: 12px; font-size: 0.9rem; font-weight: 500; cursor: pointer; width: 100%; margin-top: 1rem; }
        button:hover { background: #2563eb; transform: translateY(-1px); }
        button:disabled { opacity: 0.5; cursor: not-allowed; }
        .result-card { background: white; border-radius: 24px; border: 1px solid #e5e7eb; padding: 2rem; display: none; }
        .result-header { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 1rem; padding-bottom: 1rem; border-bottom: 1px solid #e5e7eb; }
        .result-content { line-height: 1.7; color: #1f2937; font-size: 0.95rem; }
        .result-content strong { font-weight: 600; color: #3b82f6; }
        .result-content em { font-style: italic; }
        .result-content code { background: #f3f4f6; padding: 2px 4px; border-radius: 4px; font-family: monospace; font-size: 0.85rem; }
        .result-content h1, .result-content h2, .result-content h3 { margin-top: 1rem; margin-bottom: 0.5rem; }
        .result-content ul, .result-content ol { margin-left: 1.5rem; margin-bottom: 1rem; }
        .result-content li { margin-bottom: 0.25rem; }
        .result-meta { margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #e5e7eb; font-size: 0.7rem; color: #9ca3af; }
        .loading { display: none; text-align: center; padding: 2rem; }
        .spinner { width: 40px; height: 40px; border: 3px solid #e5e7eb; border-top-color: #3b82f6; border-radius: 50%; animation: spin 0.8s linear infinite; margin: 0 auto 1rem; }
        @keyframes spin { to { transform: rotate(360deg); } }
    </style>
</head>
<body>
<div class="app">
    <div class="sidebar">
        <div><div class="logo"><span class="logo-icon">📖</span><span class="logo-text">Lurnic</span></div><div class="tagline">ask anything. study anything.</div></div>
        <div class="nav-section"><div class="nav-title">mode</div>
            <div class="mode-card" data-mode="direct"><div class="mode-name">✨ Ask Anything</div><div class="mode-desc">No PDF needed. General questions.</div></div>
            <div class="mode-card" data-mode="pdf"><div class="mode-name">📚 Study Textbook</div><div class="mode-desc">Upload PDF. Ask about content.</div></div>
        </div>
        <div class="nav-section"><div class="nav-title">plan</div>
            <div class="tier-card" data-tier="free"><div class="tier-name">Free</div><div class="tier-desc">standard responses</div><span class="badge badge-free">limited</span></div>
            <div class="tier-card" data-tier="paid"><div class="tier-name">Premium</div><div class="tier-desc">faster + diagrams + tables</div><span class="badge badge-paid">unlimited</span></div>
        </div>
        <div class="info-box"><p>✨ <strong>How it works</strong></p><p><strong>Ask Anything:</strong> Just type your question — like ChatGPT.</p><p><strong>Study Textbook:</strong> Upload PDF + ask questions about it.</p><p style="margin-top: 0.75rem;">🔒 Your data is never stored.</p></div>
    </div>
    <div class="main-content">
        <div class="upload-card" id="uploadCard"><div class="upload-area" id="uploadArea"><div class="upload-icon">📄</div><div class="upload-text">Click or drag to upload a PDF</div><input type="file" id="fileInput" accept=".pdf" style="display: none;"><div class="file-name" id="fileName"></div></div></div>
        <div class="question-area"><label id="questionLabel">Your question</label><textarea id="questionInput" rows="3" placeholder="e.g., What is photosynthesis?"></textarea></div>
        <button id="askButton">Ask Lurnic →</button>
        <div class="loading" id="loading"><div class="spinner"></div><p>Lurnic is thinking...</p></div>
        <div class="result-card" id="resultCard"><div class="result-header"><span>✨</span><h3>Answer</h3></div><div class="result-content" id="answerText"></div><div class="result-meta" id="metaInfo"></div></div>
    </div>
</div>
<script>
    const modeCards = document.querySelectorAll('.mode-card');
    const tierCards = document.querySelectorAll('.tier-card');
    const uploadCard = document.getElementById('uploadCard');
    const fileInput = document.getElementById('fileInput');
    const uploadArea = document.getElementById('uploadArea');
    const fileNameSpan = document.getElementById('fileName');
    const questionInput = document.getElementById('questionInput');
    const questionLabel = document.getElementById('questionLabel');
    const askButton = document.getElementById('askButton');
    const loadingDiv = document.getElementById('loading');
    const resultCard = document.getElementById('resultCard');
    const answerText = document.getElementById('answerText');
    const metaInfo = document.getElementById('metaInfo');
    let selectedMode = 'direct';
    let selectedTier = 'free';
    let selectedFile = null;

    // Enter key submits (Ctrl+Enter for new line)
    questionInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.ctrlKey && !e.shiftKey) {
            e.preventDefault();
            askButton.click();
        }
    });

    // Mode selection
    modeCards.forEach(card => {
        card.addEventListener('click', () => {
            modeCards.forEach(c => c.classList.remove('selected'));
            card.classList.add('selected');
            selectedMode = card.dataset.mode;
            if (selectedMode === 'pdf') {
                uploadCard.classList.add('visible');
                questionLabel.textContent = 'Your question about the textbook';
                questionInput.placeholder = 'e.g., How does Chapter 3 relate to Chapter 12?';
            } else {
                uploadCard.classList.remove('visible');
                questionLabel.textContent = 'Your question';
                questionInput.placeholder = 'e.g., What is photosynthesis?';
                selectedFile = null;
                fileNameSpan.style.display = 'none';
            }
        });
    });

    // Tier selection
    tierCards.forEach(card => {
        card.addEventListener('click', () => {
            tierCards.forEach(c => c.classList.remove('selected'));
            card.classList.add('selected');
            selectedTier = card.dataset.tier;
        });
    });

    // Set defaults
    document.querySelector('.mode-card[data-mode="direct"]').classList.add('selected');
    document.querySelector('.tier-card[data-tier="free"]').classList.add('selected');

    // File upload handlers
    uploadArea.addEventListener('click', () => { if (selectedMode === 'pdf') fileInput.click(); });
    uploadArea.addEventListener('dragover', (e) => { e.preventDefault(); if (selectedMode === 'pdf') uploadArea.style.borderColor = '#3b82f6'; });
    uploadArea.addEventListener('dragleave', () => { uploadArea.style.borderColor = '#e5e7eb'; });
    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.style.borderColor = '#e5e7eb';
        if (selectedMode === 'pdf') {
            const files = e.dataTransfer.files;
            if (files.length > 0 && files[0].type === 'application/pdf') handleFile(files[0]);
            else alert('Please drop a PDF file');
        }
    });
    fileInput.addEventListener('change', (e) => { if (e.target.files.length > 0) handleFile(e.target.files[0]); });
    
    function handleFile(file) { 
        selectedFile = file; 
        fileNameSpan.textContent = file.name; 
        fileNameSpan.style.display = 'block'; 
        uploadArea.style.borderColor = '#3b82f6'; 
    }

    // Markdown to HTML converter
    function convertMarkdownToHtml(text) {
        if (!text) return '';
        let html = text;
        html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        html = html.replace(/__(.*?)__/g, '<strong>$1</strong>');
        html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
        html = html.replace(/_(.*?)_/g, '<em>$1</em>');
        html = html.replace(/`(.*?)`/g, '<code>$1</code>');
        html = html.replace(/### (.*?)(\n|$)/g, '<h3>$1</h3>');
        html = html.replace(/## (.*?)(\n|$)/g, '<h2>$1</h2>');
        html = html.replace(/# (.*?)(\n|$)/g, '<h1>$1</h1>');
        html = html.replace(/^[\*\-] (.*?)$/gm, '<li>$1</li>');
        html = html.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');
        html = html.replace(/\n/g, '<br>');
        return html;
    }

    // Ask button handler
    askButton.addEventListener('click', async () => {
        console.log("Ask button clicked");
        
        const question = questionInput.value.trim();
        if (!question) { 
            alert('Please enter a question'); 
            return; 
        }
        
        if (selectedMode === 'pdf' && !selectedFile) { 
            alert('Please upload a PDF file for textbook mode'); 
            return; 
        }
        
        // Show loading, hide previous result
        loadingDiv.style.display = 'block';
        resultCard.style.display = 'none';
        askButton.disabled = true;
        
        const formData = new FormData();
        formData.append('question', question);
        formData.append('mode', selectedMode);
        formData.append('tier', selectedTier);
        if (selectedMode === 'pdf' && selectedFile) {
            formData.append('pdf_file', selectedFile);
        }
        
        try {
            console.log("Sending request...");
            const response = await fetch('/ask', { 
                method: 'POST', 
                body: formData 
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            console.log("Response received");
            
            loadingDiv.style.display = 'none';
            resultCard.style.display = 'block';
            answerText.innerHTML = convertMarkdownToHtml(data.answer);
            metaInfo.innerHTML = `${data.method_used || 'unknown'} · ${data.processing_time || 0}s · ${data.images_processed || 0} images`;
        } catch (error) {
            console.error("Error:", error);
            loadingDiv.style.display = 'none';
            alert('Error: ' + error.message);
        } finally { 
            askButton.disabled = false; 
        }
    });
    
    console.log("Page loaded, script ready");
</script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def root():
    return HTML_TEMPLATE

@app.post("/ask")
async def ask_question(
    pdf_file: UploadFile = File(None),
    question: str = Form(...),
    mode: str = Form("direct"),
    tier: str = Form("free")
):
    start_time = time.time()
    if mode == "pdf" and pdf_file:
        if not pdf_file.filename.endswith('.pdf'):
            raise HTTPException(400, "Only PDF files are accepted")
        pdf_bytes = await pdf_file.read()
        if len(pdf_bytes) > 50 * 1024 * 1024:
            raise HTTPException(400, "File too large. Max 50MB.")
        result = process_pdf(pdf_bytes, question, tier=tier)
        processing_time = time.time() - start_time
        return {
            "answer": result.get("answer", "No answer generated"),
            "method_used": result.get("method_used", "pdf_processing"),
            "images_processed": result.get("images_processed", 0),
            "processing_time": round(processing_time, 2),
            "mode": "pdf"
        }
    else:
        result = ask_gemini_direct(question, tier=tier)
        return {
            "answer": result.get("answer", "No answer generated"),
            "method_used": result.get("method_used", "direct_ai"),
            "images_processed": 0,
            "processing_time": result.get("processing_time", 0),
            "mode": "direct"
        }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "models": {"free": Config.MODEL_FREE, "paid": Config.MODEL_PAID}}

print("✓ API loaded successfully (with Markdown rendering)")