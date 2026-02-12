(() => {
    const fileInput = document.getElementById("fileInput");
    const browseBtn = document.getElementById("browseBtn");
    const uploadBox = document.getElementById("uploadBox");
    const clearSessionUrl = uploadBox?.dataset?.clearSessionUrl || "";
    const collectionSelect = document.getElementById("collectionSelect");
    const selectedFilesText = document.getElementById("selectedFilesText");
    const uploadProgressWrap = document.getElementById("uploadProgressWrap");
    const uploadProgressBar = document.getElementById("uploadProgressBar");
    const uploadProgressText = document.getElementById("uploadProgressText");
    const searchInput = document.getElementById("fileSearch");
    const searchResults = document.getElementById("searchResults");
    const fileList = document.getElementById("fileList");
    const fileCount = document.getElementById("fileCount");
    const clearSearch = document.getElementById("clearSearch");
    const filterChips = Array.from(document.querySelectorAll(".filter-chip"));

    const metricTotalFiles = document.getElementById("metricTotalFiles");
    const metricStorage = document.getElementById("metricStorage");
    const metricTypes = document.getElementById("metricTypes");
    const metricActivity = document.getElementById("metricActivity");

    if (!fileList) return;

    const extensionOf = (name) => {
        const parts = (name || "").split(".");
        return parts.length > 1 ? parts[parts.length - 1].toLowerCase() : "file";
    };

    const typeOf = (name) => {
        const ext = extensionOf(name);
        if (["pdf", "doc", "docx", "txt", "md", "ppt", "pptx"].includes(ext)) return "docs";
        if (["png", "jpg", "jpeg", "gif", "svg", "webp"].includes(ext)) return "images";
        if (["csv", "xls", "xlsx"].includes(ext)) return "sheets";
        return "other";
    };

    const formatSize = (bytes) => {
        if (!bytes || bytes < 1024) return `${bytes || 0} B`;
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
        return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
    };

    const allCards = () => Array.from(fileList.querySelectorAll(".file-card[data-file]"));
    const fileName = (card) => card.dataset.file || "";
    const fileSearchText = (card) => (card.dataset.search || card.dataset.file || "").toLowerCase();
    const allFileNames = () => allCards().map((card) => fileName(card));

    let activeFilter = "all";
    let isUploading = false;
    let suppressSessionClear = false;

    const uploadButtons = uploadBox
        ? Array.from(uploadBox.querySelectorAll("button, input, select, textarea"))
        : [];

    const updateMetrics = () => {
        const cards = allCards();
        const names = cards.map((card) => fileName(card));
        const totalSize = cards.reduce((sum, card) => sum + Number(card.dataset.size || 0), 0);
        const typeCount = new Set(names.map((name) => extensionOf(name))).size;

        metricTotalFiles.textContent = String(cards.length);
        metricStorage.textContent = formatSize(totalSize);
        metricTypes.textContent = String(typeCount);
        metricActivity.textContent = cards.length ? new Date().toLocaleDateString() : "-";
    };

    const applyFilters = () => {
        const q = (searchInput.value || "").trim().toLowerCase();
        const cards = allCards();

        cards.forEach((card) => {
            const name = fileSearchText(card);
            const inFilter = activeFilter === "all" || typeOf(name) === activeFilter;
            const inSearch = !q || name.includes(q);
            card.style.display = inFilter && inSearch ? "" : "none";
        });

        const visibleCount = cards.filter((card) => card.style.display !== "none").length;
        fileCount.textContent = `${visibleCount} file${visibleCount === 1 ? "" : "s"}`;
    };

    const showResults = () => {
        const q = (searchInput.value || "").trim().toLowerCase();
        if (!q) {
            searchResults.style.display = "none";
            searchResults.innerHTML = "";
            return;
        }

        const results = allCards()
            .map((card) => ({ display: fileName(card), search: fileSearchText(card) }))
            .filter((item) => item.search.includes(q))
            .map((item) => item.display)
            .slice(0, 8);
        if (!results.length) {
            searchResults.innerHTML = '<div class="search-item" aria-disabled="true">No matching file</div>';
            searchResults.style.display = "block";
            return;
        }

        searchResults.innerHTML = results
            .map((name) => `<button class="search-item" type="button" data-value="${name}">${name}</button>`)
            .join("");
        searchResults.style.display = "block";
    };

    const updateSelectedFilesLabel = () => {
        if (!selectedFilesText) return;
        const count = fileInput?.files?.length || 0;
        selectedFilesText.textContent = count ? `${count} file(s) selected.` : "No files selected.";
    };

    const setUploadingState = (uploading) => {
        isUploading = uploading;
        uploadButtons.forEach((el) => {
            if (!el || el.type === "hidden") return;
            el.disabled = uploading;
        });
    };

    const beforeUnloadHandler = (event) => {
        if (!isUploading) return;
        event.preventDefault();
        event.returnValue = "";
    };

    if (browseBtn && fileInput) {
        browseBtn.addEventListener("click", () => fileInput.click());
        fileInput.addEventListener("change", updateSelectedFilesLabel);
    }

    if (uploadBox && fileInput) {
        ["dragenter", "dragover"].forEach((type) => {
            uploadBox.addEventListener(type, (event) => {
                event.preventDefault();
                uploadBox.classList.add("drag-over");
            });
        });

        ["dragleave", "drop"].forEach((type) => {
            uploadBox.addEventListener(type, (event) => {
                event.preventDefault();
                uploadBox.classList.remove("drag-over");
            });
        });

        uploadBox.addEventListener("drop", (event) => {
            const dropped = event.dataTransfer?.files;
            if (!dropped || !dropped.length) return;

            const dt = new DataTransfer();
            Array.from(dropped).forEach((file) => dt.items.add(file));
            fileInput.files = dt.files;
            updateSelectedFilesLabel();
        });

        uploadBox.addEventListener("submit", (event) => {
            event.preventDefault();

            if (isUploading) return;
            suppressSessionClear = true;

            const formData = new FormData(uploadBox);
            const filesCount = fileInput?.files?.length || 0;
            const selectedCollection = collectionSelect?.value || "";
            if (!selectedCollection) {
                if (selectedFilesText) selectedFilesText.textContent = "Please choose a collection before upload.";
                return;
            }
            if (!filesCount) {
                if (selectedFilesText) selectedFilesText.textContent = "Please choose files before upload.";
                return;
            }

            setUploadingState(true);
            if (uploadProgressWrap) uploadProgressWrap.hidden = false;
            window.addEventListener("beforeunload", beforeUnloadHandler);

            if (uploadProgressBar) uploadProgressBar.value = 5;
            if (uploadProgressText) uploadProgressText.textContent = "Uploading... 0%";

            const xhr = new XMLHttpRequest();
            xhr.open("POST", uploadBox.action || window.location.href, true);
            xhr.setRequestHeader("X-Requested-With", "XMLHttpRequest");

            xhr.upload.addEventListener("progress", (e) => {
                if (!e.lengthComputable) {
                    if (uploadProgressText) uploadProgressText.textContent = "Uploading...";
                    return;
                }
                const percent = Math.min(100, Math.round((e.loaded / e.total) * 100));
                if (uploadProgressBar) uploadProgressBar.value = percent;
                if (uploadProgressText) uploadProgressText.textContent = `Uploading... ${percent}%`;
            });

            xhr.addEventListener("load", () => {
                window.removeEventListener("beforeunload", beforeUnloadHandler);
                if (xhr.status >= 200 && xhr.status < 400) {
                    if (uploadProgressBar) uploadProgressBar.value = 100;
                    if (uploadProgressText) uploadProgressText.textContent = "Upload complete. Refreshing...";
                    setTimeout(() => window.location.reload(), 700);
                    return;
                }
                setUploadingState(false);
                suppressSessionClear = false;
                if (uploadProgressBar) uploadProgressBar.value = 0;
                if (uploadProgressText) uploadProgressText.textContent = "Upload failed. Try again.";
            });

            xhr.addEventListener("error", () => {
                window.removeEventListener("beforeunload", beforeUnloadHandler);
                setUploadingState(false);
                suppressSessionClear = false;
                if (uploadProgressBar) uploadProgressBar.value = 0;
                if (uploadProgressText) uploadProgressText.textContent = "Upload failed. Check connection and retry.";
            });

            xhr.send(formData);
        });
    }

    if (searchInput) {
        searchInput.addEventListener("input", () => {
            applyFilters();
            showResults();
        });
    }

    if (searchResults) {
        searchResults.addEventListener("click", (event) => {
            const item = event.target.closest("button[data-value]");
            if (!item) return;

            const value = item.dataset.value || "";
            searchInput.value = value;
            searchResults.style.display = "none";
            applyFilters();

            const target = allCards().find((card) => fileName(card) === value);
            if (!target) return;
            allCards().forEach((card) => card.classList.remove("active"));
            target.classList.add("active");
            target.scrollIntoView({ behavior: "smooth", block: "nearest" });
        });
    }

    if (clearSearch) {
        clearSearch.addEventListener("click", () => {
            searchInput.value = "";
            searchResults.style.display = "none";
            allCards().forEach((card) => card.classList.remove("active"));
            applyFilters();
        });
    }

    filterChips.forEach((chip) => {
        chip.addEventListener("click", () => {
            activeFilter = chip.dataset.filter || "all";
            filterChips.forEach((item) => item.classList.toggle("active", item === chip));
            applyFilters();
            showResults();
        });
    });

    document.addEventListener("click", (event) => {
        if (!event.target.closest(".search-wrap")) {
            searchResults.style.display = "none";
        }
    });

    document.querySelectorAll("form[action]").forEach((form) => {
        form.addEventListener("submit", () => {
            const action = form.getAttribute("action") || "";
            if (action.includes("/files/delete/")) {
                suppressSessionClear = true;
            }
        });
    });

    window.addEventListener("pagehide", () => {
        if (suppressSessionClear || !clearSessionUrl) return;
        navigator.sendBeacon(clearSessionUrl, new Blob([], { type: "text/plain" }));
    });

    updateMetrics();
    applyFilters();
    updateSelectedFilesLabel();
})();
