/**
 * RockyBot AI - Client Application Logic
 * Modern, responsive financial and news research assistant
 */

document.addEventListener("DOMContentLoaded", () => {
  // DOM References
  const urlInputsList = document.getElementById("url-inputs-list");
  const addUrlBtn = document.getElementById("add-url-btn");
  const urlCountIndicator = document.getElementById("url-count-indicator");
  const processUrlsBtn = document.getElementById("process-urls-btn");
  const sampleChips = document.querySelectorAll(".chip-btn");
  const resetWorkspaceBtn = document.getElementById("reset-workspace-btn");

  const systemStatusBadge = document.getElementById("system-status-badge");
  const systemStatusText = document.getElementById("system-status-text");

  const ingestionProgressCard = document.getElementById("ingestion-progress-card");
  const activeKnowledgeCard = document.getElementById("active-knowledge-card");
  const activeIndexStats = document.getElementById("active-index-stats");
  const activeSourcesList = document.getElementById("active-sources-list");

  const promptChips = document.querySelectorAll(".prompt-chip");
  const queryInput = document.getElementById("query-input");
  const submitQueryBtn = document.getElementById("submit-query-btn");
  const qaEmptyState = document.getElementById("qa-empty-state");
  const qaLoadingView = document.getElementById("qa-loading-view");
  const qaResultContainer = document.getElementById("qa-result-container");
  const resultAnswerText = document.getElementById("result-answer-text");
  const resultSourcesList = document.getElementById("result-sources-list");
  const resultTimestamp = document.getElementById("result-timestamp");
  const copyAnswerBtn = document.getElementById("copy-answer-btn");
  const copyBtnText = document.getElementById("copy-btn-text");
  const toastContainer = document.getElementById("toast-container");

  // Sample Datasets for Fast Demo
  const SAMPLES = {
    nvidia: [
      "https://en.wikipedia.org/wiki/Nvidia"
    ],
    tata: [
      "https://www.moneycontrol.com/news/business/tata-motors-launches-punch-icng-price-starts-at-rs-7-1-lakh-11098751.html"
    ],
    multi: [
      "https://www.moneycontrol.com/news/business/tata-motors-launches-punch-icng-price-starts-at-rs-7-1-lakh-11098751.html",
      "https://www.moneycontrol.com/news/business/stocks/buy-tata-motors-target-of-rs-743-kr-choksey-11080811.html"
    ]
  };

  // Toast Notification System
  function showToast(message, type = "info", duration = 4000) {
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    
    let iconSvg = "";
    if (type === "success") {
      iconSvg = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2"><polyline points="20 6 9 17 4 12"></polyline></svg>`;
    } else if (type === "error") {
      iconSvg = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#f43f5e" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>`;
    } else {
      iconSvg = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#06b6d4" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>`;
    }

    toast.innerHTML = `${iconSvg}<span>${escapeHtml(message)}</span>`;
    toastContainer.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transform = "translateY(20px)";
      toast.style.transition = "all 0.3s ease";
      setTimeout(() => toast.remove(), 300);
    }, duration);
  }

  function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  // Manage Dynamic URL Inputs
  function updateUrlRowsState() {
    const rows = urlInputsList.querySelectorAll(".url-input-row");
    const count = rows.length;
    
    // Update count indicator
    let filledCount = 0;
    rows.forEach(row => {
      const input = row.querySelector(".url-input");
      if (input && input.value.trim()) filledCount++;
    });

    urlCountIndicator.textContent = filledCount === 1 
      ? "1 link ready" 
      : `${filledCount} links ready (${count} fields)`;

    // Show/hide remove button based on row count
    rows.forEach(row => {
      const removeBtn = row.querySelector(".btn-remove-url");
      if (removeBtn) {
        removeBtn.style.display = count > 1 ? "flex" : "none";
      }
    });
  }

  function createUrlRow(value = "") {
    const row = document.createElement("div");
    row.className = "url-input-row";
    row.innerHTML = `
      <div class="input-icon">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path>
          <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path>
        </svg>
      </div>
      <input 
        type="url" 
        class="form-control url-input" 
        placeholder="https://example.com/financial-news-article" 
        value="${escapeHtml(value)}"
        autocomplete="off"
        spellcheck="false"
      />
      <button type="button" class="btn-remove-url" title="Remove URL">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="18" y1="6" x2="6" y2="18"></line>
          <line x1="6" y1="6" x2="18" y2="18"></line>
        </svg>
      </button>
    `;

    const removeBtn = row.querySelector(".btn-remove-url");
    removeBtn.addEventListener("click", () => {
      row.remove();
      updateUrlRowsState();
    });

    const input = row.querySelector(".url-input");
    input.addEventListener("input", updateUrlRowsState);

    return row;
  }

  addUrlBtn.addEventListener("click", () => {
    const newRow = createUrlRow("");
    urlInputsList.appendChild(newRow);
    const input = newRow.querySelector(".url-input");
    if (input) input.focus();
    updateUrlRowsState();
  });

  // Attach listener to initial row
  const initialInput = urlInputsList.querySelector(".url-input");
  if (initialInput) {
    initialInput.addEventListener("input", updateUrlRowsState);
  }

  // Quick Samples
  sampleChips.forEach(chip => {
    chip.addEventListener("click", () => {
      const key = chip.dataset.sample;
      const urls = SAMPLES[key] || [];
      if (!urls.length) return;

      urlInputsList.innerHTML = "";
      urls.forEach(u => {
        urlInputsList.appendChild(createUrlRow(u));
      });
      updateUrlRowsState();
      showToast(`Loaded sample URL(s) for ${chip.textContent.trim()}`, "info", 2500);
    });
  });

  // Check Backend Status on Launch
  async function checkSystemStatus() {
    try {
      const res = await fetch("/api/status");
      if (!res.ok) throw new Error("Failed to reach server");
      const data = await res.json();

      if (data.api_key_configured) {
        systemStatusBadge.className = "status-indicator ready";
        systemStatusText.textContent = "Gemini 2.0 Connected";
      } else {
        systemStatusBadge.className = "status-indicator warning";
        systemStatusText.textContent = "API Key Missing (.env)";
      }

      if (data.index_ready && data.metadata) {
        renderActiveKnowledge(data.metadata);
      } else if (data.index_ready) {
        activeKnowledgeCard.style.display = "flex";
        activeIndexStats.textContent = "Existing index loaded in memory";
      }
    } catch (err) {
      systemStatusBadge.className = "status-indicator warning";
      systemStatusText.textContent = "Connecting to Server...";
    }
  }

  function renderActiveKnowledge(metadata) {
    if (!metadata || !metadata.sources || !metadata.sources.length) {
      activeKnowledgeCard.style.display = "none";
      return;
    }

    activeKnowledgeCard.style.display = "flex";
    const count = metadata.sources.length;
    const chunks = metadata.chunk_count || 0;
    activeIndexStats.textContent = `${count} article${count > 1 ? "s" : ""} | ${chunks} searchable chunks`;

    activeSourcesList.innerHTML = "";
    metadata.sources.forEach(src => {
      const li = document.createElement("li");
      li.className = "active-source-item";
      li.innerHTML = `
        <span class="source-domain-pill">${escapeHtml(src.domain || "web")}</span>
        <a href="${escapeHtml(src.url)}" target="_blank" rel="noopener noreferrer" class="source-link-out" title="${escapeHtml(src.url)}">
          <span>Open link</span>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
            <polyline points="15 3 21 3 21 9"></polyline>
            <line x1="10" y1="14" x2="21" y2="3"></line>
          </svg>
        </a>
      `;
      activeSourcesList.appendChild(li);
    });
  }

  // Stepper Animation Utility
  function setProgressStep(stepId, state) {
    const el = document.getElementById(stepId);
    if (!el) return;
    el.classList.remove("active", "completed");
    if (state === "active") el.classList.add("active");
    if (state === "completed") el.classList.add("completed");
  }

  // Process & Index URLs
  processUrlsBtn.addEventListener("click", async () => {
    const inputs = urlInputsList.querySelectorAll(".url-input");
    const urls = [];
    inputs.forEach(input => {
      const val = input.value.trim();
      if (val) urls.push(val);
    });

    if (urls.length === 0) {
      showToast("Please enter at least 1 URL to proceed.", "error");
      inputs[0]?.focus();
      return;
    }

    // Set UI to loading state
    processUrlsBtn.disabled = true;
    processUrlsBtn.querySelector(".btn-text").textContent = "Indexing Content...";
    ingestionProgressCard.style.display = "flex";

    setProgressStep("step-fetch", "active");
    setProgressStep("step-chunk", "");
    setProgressStep("step-embed", "");
    setProgressStep("step-faiss", "");

    try {
      // Step simulation indicators while awaiting backend
      setTimeout(() => setProgressStep("step-fetch", "completed"), 1200);
      setTimeout(() => setProgressStep("step-chunk", "active"), 1300);
      setTimeout(() => setProgressStep("step-chunk", "completed"), 2200);
      setTimeout(() => setProgressStep("step-embed", "active"), 2300);

      const response = await fetch("/api/process-urls", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ urls })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Error processing articles.");
      }

      setProgressStep("step-embed", "completed");
      setProgressStep("step-faiss", "completed");

      showToast(`Success! Indexed ${data.articles_indexed} article(s) into ${data.total_chunks} vectors.`, "success", 5000);

      // Refresh active status
      await checkSystemStatus();

      // Show friendly query tip
      if (qaEmptyState.style.display !== "none") {
        queryInput.placeholder = "Now ask any question about the article you just indexed...";
        queryInput.focus();
      }

    } catch (err) {
      showToast(err.message, "error", 6000);
    } finally {
      processUrlsBtn.disabled = false;
      processUrlsBtn.querySelector(".btn-text").textContent = "Build Knowledge Index";
      setTimeout(() => {
        ingestionProgressCard.style.display = "none";
      }, 1500);
    }
  });

  // Prompt Chips Handler
  promptChips.forEach(chip => {
    chip.addEventListener("click", () => {
      const promptText = chip.dataset.prompt;
      queryInput.value = promptText;
      queryInput.focus();
      handleQuerySubmission();
    });
  });

  // Submit Query on Button or Enter
  submitQueryBtn.addEventListener("click", handleQuerySubmission);

  queryInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleQuerySubmission();
    }
  });

  async function handleQuerySubmission() {
    const question = queryInput.value.trim();
    if (!question) {
      showToast("Please enter a question to ask RockyBot.", "error");
      queryInput.focus();
      return;
    }

    // Switch views to loading
    qaEmptyState.style.display = "none";
    qaResultContainer.style.display = "none";
    qaLoadingView.style.display = "flex";
    submitQueryBtn.disabled = true;

    try {
      const response = await fetch("/api/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Failed to generate answer.");
      }

      // Render Answer
      renderAnswer(data.answer, data.sources);
      qaLoadingView.style.display = "none";
      qaResultContainer.style.display = "block";

    } catch (err) {
      qaLoadingView.style.display = "none";
      qaEmptyState.style.display = "flex";
      showToast(err.message, "error", 5000);
    } finally {
      submitQueryBtn.disabled = false;
    }
  }

  function renderAnswer(answerText, sources) {
    // Format simple markdown into HTML
    const formattedHtml = formatMarkdownToHtml(answerText);
    resultAnswerText.innerHTML = formattedHtml;

    resultTimestamp.textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    // Render Sources
    resultSourcesList.innerHTML = "";
    if (sources && sources.length > 0) {
      sources.forEach(src => {
        const a = document.createElement("a");
        a.className = "source-citation-card";
        a.href = src.url;
        a.target = "_blank";
        a.rel = "noopener noreferrer";
        a.innerHTML = `
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path>
            <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path>
          </svg>
          <span class="source-citation-domain">${escapeHtml(src.domain || "Source Link")}</span>
        `;
        resultSourcesList.appendChild(a);
      });
    } else {
      resultSourcesList.innerHTML = `<span style="font-size: 0.8rem; color: var(--text-muted);">Direct synthesis from indexed context</span>`;
    }
  }

  function formatMarkdownToHtml(markdown) {
    if (!markdown) return "";
    let html = escapeHtml(markdown);

    // Bold text: **text**
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

    // Bullet points: * or -
    const lines = html.split("\n");
    let inList = false;
    let processed = [];

    lines.forEach(line => {
      const trimmed = line.trim();
      if (trimmed.startsWith("* ") || trimmed.startsWith("- ")) {
        if (!inList) {
          processed.push("<ul>");
          inList = true;
        }
        processed.push(`<li>${trimmed.substring(2)}</li>`);
      } else {
        if (inList) {
          processed.push("</ul>");
          inList = false;
        }
        if (trimmed) {
          processed.push(`<p>${trimmed}</p>`);
        }
      }
    });

    if (inList) processed.push("</ul>");
    return processed.join("");
  }

  // Copy Answer to Clipboard
  copyAnswerBtn.addEventListener("click", async () => {
    const rawText = resultAnswerText.innerText;
    if (!rawText) return;

    try {
      await navigator.clipboard.writeText(rawText);
      copyBtnText.textContent = "Copied!";
      showToast("Answer copied to clipboard!", "success", 2000);
      setTimeout(() => {
        copyBtnText.textContent = "Copy";
      }, 2000);
    } catch (e) {
      showToast("Failed to copy to clipboard", "error");
    }
  });

  // Reset Index
  resetWorkspaceBtn.addEventListener("click", async () => {
    if (!confirm("Are you sure you want to clear the active knowledge index? You can index new articles anytime.")) {
      return;
    }

    try {
      const res = await fetch("/api/reset", { method: "POST" });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Reset failed");

      showToast("Knowledge base reset successfully.", "info");
      activeKnowledgeCard.style.display = "none";
      qaResultContainer.style.display = "none";
      qaEmptyState.style.display = "flex";
      queryInput.value = "";
      updateUrlRowsState();
    } catch (err) {
      showToast(err.message, "error");
    }
  });

  // Initial Check
  checkSystemStatus();
  updateUrlRowsState();
});
