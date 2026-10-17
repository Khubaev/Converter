(() => {
  const API = "/api/v1/conversions";
  const POLL_MS = 500;
  const TIMEOUT_MS = 120_000;

  const form = document.getElementById("convert-form");
  const fileInput = document.getElementById("file");
  const fileName = document.getElementById("file-name");
  const targetSelect = document.getElementById("target_format");
  const submitBtn = document.getElementById("submit-btn");
  const statusBox = document.getElementById("status");
  const statusValue = document.getElementById("status-value");
  const jobIdEl = document.getElementById("job-id");
  const statusDetail = document.getElementById("status-detail");
  const downloadBtn = document.getElementById("download-btn");
  const recognizeBtn = document.getElementById("recognize-btn");
  const ocrBox = document.getElementById("ocr");
  const ocrFold = document.getElementById("ocr-fold");
  const promptFold = document.getElementById("prompt-fold");
  const ocrText = document.getElementById("ocr-text");
  const ocrDownload = document.getElementById("ocr-download");
  const assembleBtn = document.getElementById("assemble-btn");
  const assembleStatus = document.getElementById("assemble-status");
  const assemblyJson = document.getElementById("assembly-json");
  const assemblyDownload = document.getElementById("assembly-download");
  const promptSelect = document.getElementById("prompt-select");
  const promptText = document.getElementById("prompt-text");
  const errorEl = document.getElementById("error");
  const dpiInput = document.getElementById("dpi");
  const dpiHint = document.getElementById("dpi-hint");

  let currentJobId = null;
  let ocrObjectUrl = null;
  let assemblyObjectUrl = null;
  const promptsById = new Map();

  function showError(message) {
    errorEl.hidden = false;
    errorEl.textContent = message;
  }

  function clearError() {
    errorEl.hidden = true;
    errorEl.textContent = "";
  }

  function setBusy(busy) {
    submitBtn.disabled = busy;
    submitBtn.textContent = busy ? "Конвертация…" : "Конвертировать";
  }

  function setRecognizeBusy(busy) {
    recognizeBtn.disabled = busy;
    recognizeBtn.textContent = busy ? "Распознавание…" : "Распознать текст";
  }

  function showStatus(jobId, status, detail) {
    statusBox.hidden = false;
    jobIdEl.textContent = jobId;
    statusValue.textContent = status;
    statusValue.dataset.state = status;
    if (detail) {
      statusDetail.hidden = false;
      statusDetail.textContent = detail;
    } else {
      statusDetail.hidden = true;
      statusDetail.textContent = "";
    }
  }

  function hideDownload() {
    downloadBtn.hidden = true;
    downloadBtn.removeAttribute("href");
    downloadBtn.removeAttribute("download");
  }

  function hideAssemblyDocument() {
    assemblyJson.hidden = true;
    assemblyJson.textContent = "";
    assemblyDownload.hidden = true;
    assemblyDownload.removeAttribute("href");
    assemblyDownload.removeAttribute("download");
    if (assemblyObjectUrl) {
      URL.revokeObjectURL(assemblyObjectUrl);
      assemblyObjectUrl = null;
    }
  }

  function hideAssembleStatus() {
    assembleStatus.hidden = true;
    assembleStatus.textContent = "";
    hideAssemblyDocument();
  }

  function showAssemblyDocument(document, jobId) {
    const pretty = JSON.stringify(document, null, 2);
    assemblyJson.hidden = false;
    assemblyJson.textContent = pretty;
    const blob = new Blob([pretty], { type: "application/json;charset=utf-8" });
    if (assemblyObjectUrl) {
      URL.revokeObjectURL(assemblyObjectUrl);
    }
    assemblyObjectUrl = URL.createObjectURL(blob);
    assemblyDownload.hidden = false;
    assemblyDownload.href = assemblyObjectUrl;
    assemblyDownload.download = `assembly_${jobId}.json`;
  }

  function showAssembleStatus(message) {
    assembleStatus.hidden = false;
    assembleStatus.textContent = message;
  }

  function setAssembleBusy(busy) {
    assembleBtn.disabled = busy;
    assembleBtn.textContent = busy ? "Отправка…" : "Отправить на сборку";
  }

  function collapseFolds() {
    ocrFold.open = false;
    promptFold.open = false;
  }

  function hideOcr() {
    ocrBox.hidden = true;
    collapseFolds();
    ocrText.value = "";
    ocrDownload.hidden = true;
    ocrDownload.removeAttribute("href");
    ocrDownload.removeAttribute("download");
    assembleBtn.hidden = true;
    setAssembleBusy(false);
    hideAssembleStatus();
    if (ocrObjectUrl) {
      URL.revokeObjectURL(ocrObjectUrl);
      ocrObjectUrl = null;
    }
  }

  function hideRecognize() {
    recognizeBtn.hidden = true;
    setRecognizeBusy(false);
  }

  function applySelectedPrompt() {
    const prompt = promptsById.get(promptSelect.value);
    promptText.value = prompt ? prompt.prompt : "";
  }

  async function loadPrompts() {
    const response = await fetch("/api/v1/assembly/prompts");
    if (!response.ok) {
      throw new Error("Не удалось загрузить промпты сборки");
    }
    const prompts = await response.json();
    promptsById.clear();
    promptSelect.innerHTML = "";
    for (const prompt of prompts) {
      promptsById.set(prompt.id, prompt);
      const option = document.createElement("option");
      option.value = prompt.id;
      option.textContent = prompt.title;
      promptSelect.appendChild(option);
    }
    applySelectedPrompt();
  }

  async function loadFormats() {
    const response = await fetch(`${API}/formats`);
    if (!response.ok) {
      throw new Error("Не удалось загрузить список форматов");
    }
    const pairs = await response.json();
    targetSelect.innerHTML = "";
    const targets = [...new Set(pairs.map((p) => p.target))];
    if (!targets.length) {
      const option = document.createElement("option");
      option.value = "jpeg";
      option.textContent = "jpeg";
      targetSelect.appendChild(option);
      return;
    }
    for (const target of targets) {
      const option = document.createElement("option");
      option.value = target;
      option.textContent = target;
      targetSelect.appendChild(option);
    }
  }

  function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  async function pollJob(jobId) {
    const started = Date.now();
    while (Date.now() - started < TIMEOUT_MS) {
      const response = await fetch(`${API}/${jobId}`);
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.detail || `Ошибка статуса (${response.status})`);
      }
      const job = await response.json();
      const detail =
        job.status === "completed"
          ? `Страниц: ${job.page_count ?? "—"}; layout: ${job.layout}`
          : job.error || "";
      showStatus(jobId, job.status, detail);

      if (job.status === "completed" && job.result_ready) {
        return job;
      }
      if (job.status === "failed") {
        throw new Error(job.error || "Конвертация завершилась ошибкой");
      }
      await sleep(POLL_MS);
    }
    throw new Error("Превышено время ожидания конвертации");
  }

  async function enableDownload(jobId) {
    const response = await fetch(`${API}/${jobId}/result`);
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(payload.detail || `Не удалось скачать результат (${response.status})`);
    }
    const blob = await response.blob();
    const disposition = response.headers.get("Content-Disposition") || "";
    const match = /filename="?([^";]+)"?/i.exec(disposition);
    const filename = match ? match[1] : "result.bin";
    const url = URL.createObjectURL(blob);
    downloadBtn.hidden = false;
    downloadBtn.href = url;
    downloadBtn.download = filename;
    downloadBtn.textContent = `Скачать ${filename}`;
  }

  function showOcrResult(fullText, jobId) {
    ocrBox.hidden = false;
    collapseFolds();
    ocrText.value = fullText || "(пустой текст)";
    const blob = new Blob([fullText || ""], { type: "text/plain;charset=utf-8" });
    if (ocrObjectUrl) {
      URL.revokeObjectURL(ocrObjectUrl);
    }
    ocrObjectUrl = URL.createObjectURL(blob);
    ocrDownload.hidden = false;
    ocrDownload.href = ocrObjectUrl;
    ocrDownload.download = `ocr_${jobId}.txt`;
    ocrDownload.textContent = "Скачать .txt";
    assembleBtn.hidden = false;
    hideAssembleStatus();
  }

  async function submitAssembly(jobId) {
    clearError();
    hideAssembleStatus();
    setAssembleBusy(true);
    try {
      const prompt = promptText.value.trim();
      if (!promptSelect.value || !prompt) {
        throw new Error("Выберите предварительный промпт");
      }
      const response = await fetch(`${API}/${jobId}/assemble`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt_id: promptSelect.value,
          prompt,
        }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(payload.detail || `Ошибка отправки (${response.status})`);
      }
      showAssembleStatus(payload.message || "Документ разобран");
      if (payload.document !== undefined && payload.document !== null) {
        showAssemblyDocument(payload.document, jobId);
      }
    } catch (err) {
      showError(err instanceof Error ? err.message : String(err));
    } finally {
      setAssembleBusy(false);
    }
  }

  async function recognize(jobId) {
    clearError();
    setRecognizeBusy(true);
    try {
      const response = await fetch(`${API}/${jobId}/recognize`, { method: "POST" });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(payload.detail || `Ошибка OCR (${response.status})`);
      }
      showOcrResult(payload.full_text || "", jobId);
    } catch (err) {
      showError(err instanceof Error ? err.message : String(err));
    } finally {
      setRecognizeBusy(false);
    }
  }

  function isWebpFile(file) {
    const name = (file?.name || "").toLowerCase();
    return name.endsWith(".webp") || file?.type === "image/webp";
  }

  function syncFileHint() {
    const file = fileInput.files?.[0];
    fileName.textContent = file ? file.name : "PDF или WebP до 50 МБ";
    const webp = Boolean(file && isWebpFile(file));
    dpiInput.disabled = webp;
    dpiHint.hidden = !webp;
  }

  fileInput.addEventListener("change", syncFileHint);

  recognizeBtn.addEventListener("click", () => {
    if (!currentJobId) {
      showError("Сначала выполните конвертацию");
      return;
    }
    recognize(currentJobId);
  });

  promptSelect.addEventListener("change", applySelectedPrompt);

  assembleBtn.addEventListener("click", () => {
    if (!currentJobId) {
      showError("Сначала распознайте текст");
      return;
    }
    submitAssembly(currentJobId);
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearError();
    hideDownload();
    hideRecognize();
    hideOcr();
    currentJobId = null;

    const file = fileInput.files?.[0];
    if (!file) {
      showError("Выберите PDF или WebP");
      return;
    }

    const body = new FormData();
    body.append("file", file);
    body.append("target_format", targetSelect.value);
    body.append("layout", document.getElementById("layout").value);
    body.append("dpi", document.getElementById("dpi").value);
    body.append("quality", document.getElementById("quality").value);

    setBusy(true);
    showStatus("…", "queued", "Отправка файла…");

    try {
      const response = await fetch(API, { method: "POST", body });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(payload.detail || `Ошибка загрузки (${response.status})`);
      }
      const jobId = payload.job_id;
      currentJobId = jobId;
      showStatus(jobId, payload.status || "queued", "");
      await pollJob(jobId);
      await enableDownload(jobId);
      recognizeBtn.hidden = false;
    } catch (err) {
      showError(err instanceof Error ? err.message : String(err));
      if (statusValue.textContent !== "completed") {
        statusValue.dataset.state = "failed";
      }
    } finally {
      setBusy(false);
    }
  });

  Promise.all([loadFormats(), loadPrompts()]).catch((err) => {
    showError(err instanceof Error ? err.message : String(err));
  });
})();
