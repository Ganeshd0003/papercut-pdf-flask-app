(function () {
  const dropzone = document.getElementById("dropzone");
  const fileInput = document.getElementById("fileInput");
  const fileList = document.getElementById("fileList");
  const form = document.getElementById("toolForm");
  const submitBtn = document.getElementById("submitBtn");
  const progressWrap = document.getElementById("progressWrap");
  const progressBar = document.getElementById("progressBar");
  const resultBox = document.getElementById("resultBox");
  const downloadLink = document.getElementById("downloadLink");
  const errorBox = document.getElementById("errorBox");
  const csrfToken = document.getElementById("csrfToken").value;

  let organizeOrder = null; // set once page count is known, for the 'organize' tool

  function renderFileList(files) {
    fileList.innerHTML = "";
    Array.from(files).forEach((f) => {
      const li = document.createElement("li");
      li.textContent = `📄 ${f.name} (${(f.size / 1024).toFixed(1)} KB)`;
      fileList.appendChild(li);
    });
  }

  // --- Drag & drop wiring ---
  dropzone.addEventListener("click", () => fileInput.click());
  ["dragenter", "dragover"].forEach((evt) =>
    dropzone.addEventListener(evt, (e) => { e.preventDefault(); dropzone.classList.add("dragover"); })
  );
  ["dragleave", "drop"].forEach((evt) =>
    dropzone.addEventListener(evt, (e) => { e.preventDefault(); dropzone.classList.remove("dragover"); })
  );
  dropzone.addEventListener("drop", (e) => {
    const dt = e.dataTransfer;
    if (!dt || !dt.files.length) return;
    if (MULTI) {
      fileInput.files = dt.files;
    } else {
      const singleList = new DataTransfer();
      singleList.items.add(dt.files[0]);
      fileInput.files = singleList.files;
    }
    onFilesChosen();
  });
  fileInput.addEventListener("change", onFilesChosen);

  function onFilesChosen() {
    renderFileList(fileInput.files);
    if (SLUG === "organize" && fileInput.files.length === 1) {
      fetchPageCount(fileInput.files[0]);
    }
  }

  // --- Organize tool: fetch page count, render draggable chips ---
  function fetchPageCount(file) {
    const fd = new FormData();
    fd.append("file", file);
    fd.append("csrf_token", csrfToken);
    fetch("/tools/organize/page-count", { method: "POST", body: fd })
      .then((r) => r.json())
      .then((data) => {
        if (!data.ok) { showError(data.error); return; }
        renderPageChips(data.page_count);
      })
      .catch(() => showError("Could not read PDF page count."));
  }

  function renderPageChips(count) {
    const area = document.getElementById("organizeArea");
    const container = document.getElementById("pageChips");
    if (!area || !container) return;
    area.classList.remove("d-none");
    container.innerHTML = "";
    organizeOrder = Array.from({ length: count }, (_, i) => i + 1);
    organizeOrder.forEach((n) => {
      const chip = document.createElement("div");
      chip.className = "page-chip";
      chip.draggable = true;
      chip.textContent = `Page ${n}`;
      chip.dataset.page = n;
      container.appendChild(chip);
    });
    wireDragReorder(container);
  }

  function wireDragReorder(container) {
    let dragged = null;
    container.querySelectorAll(".page-chip").forEach((chip) => {
      chip.addEventListener("dragstart", () => { dragged = chip; chip.classList.add("dragging"); });
      chip.addEventListener("dragend", () => {
        chip.classList.remove("dragging");
        organizeOrder = Array.from(container.children).map((c) => parseInt(c.dataset.page, 10));
      });
      chip.addEventListener("dragover", (e) => e.preventDefault());
      chip.addEventListener("drop", (e) => {
        e.preventDefault();
        if (dragged && dragged !== chip) {
          const children = Array.from(container.children);
          const from = children.indexOf(dragged);
          const to = children.indexOf(chip);
          if (from < to) chip.after(dragged); else chip.before(dragged);
        }
      });
    });
  }

  // --- Submit handling ---
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    errorBox.classList.add("d-none");
    resultBox.classList.add("d-none");

    if (!fileInput.files.length) {
      showError("Please choose a file first.");
      return;
    }

    const fd = new FormData();
    if (MULTI) {
      Array.from(fileInput.files).forEach((f) => fd.append("files", f));
    } else {
      fd.append("file", fileInput.files[0]);
    }
    fd.append("csrf_token", csrfToken);

    // Append every non-file input in the form (ranges, quality, angle, text, etc.)
    form.querySelectorAll("input:not([type=file]), select, textarea").forEach((el) => {
      if (el.id === "csrfToken") return;
      if (el.name) fd.append(el.name, el.value);
    });

    if (SLUG === "organize" && organizeOrder) {
      fd.append("order", organizeOrder.join(","));
    }

    const endpoint = `/tools/${SLUG}/process`;
    submitBtn.disabled = true;
    progressWrap.classList.remove("d-none");
    progressBar.style.width = "0%";

    const xhr = new XMLHttpRequest();
    xhr.open("POST", endpoint);
    xhr.upload.addEventListener("progress", (evt) => {
      if (evt.lengthComputable) {
        const pct = Math.round((evt.loaded / evt.total) * 100);
        progressBar.style.width = pct + "%";
      }
    });
    xhr.onload = () => {
      submitBtn.disabled = false;
      progressBar.style.width = "100%";
      let data;
      try { data = JSON.parse(xhr.responseText); } catch (err) { data = null; }
      if (xhr.status === 200 && data && data.ok) {
        downloadLink.href = data.download_url;
        resultBox.classList.remove("d-none");
      } else {
        showError((data && data.error) || "Something went wrong. Please try again.");
      }
    };
    xhr.onerror = () => {
      submitBtn.disabled = false;
      showError("Network error — please try again.");
    };
    xhr.send(fd);
  });

  function showError(msg) {
    errorBox.textContent = msg;
    errorBox.classList.remove("d-none");
    progressWrap.classList.add("d-none");
  }
})();
