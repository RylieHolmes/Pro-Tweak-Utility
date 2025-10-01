window.addEventListener('pywebviewready', async () => {
    // --- Global State & Element Selection ---
    let tweaksData = {};
    let tweakStates = {};

    const mainNavList = document.querySelector(".sidebar .nav-list");
    const toolsNavList = document.querySelector(".sidebar .nav-list:last-of-type");
    const closeAppBtn = document.getElementById("close-btn");
    const feedbackModal = document.getElementById("feedback-modal");
    const closeModalBtn = document.getElementById("close-modal-btn");
    const modalIcon = document.getElementById("modal-icon");
    const modalTitle = document.getElementById("modal-title");
    const modalMessage = document.getElementById("modal-message");
    const modalContent = feedbackModal.querySelector(".modal-content");
    const tweakGrid = document.querySelector(".tweak-grid");
    const pages = document.querySelectorAll(".page");
    const recommendationsContainer = document.getElementById("recommendations-container");

    // --- UI Generation ---
    function createTweakCard(tweak) {
        const card = document.createElement("div");
        card.className = "tweak-card";
        card.dataset.tweakId = tweak.id;
        card.innerHTML = `
            <div class="card-header">
                <i class="fas fa-cogs card-icon"></i>
                <i class="fas fa-check-circle status-icon"></i>
            </div>
            <h3>${tweak.title}</h3>
            <p>${tweak.description}</p>
            <button class="apply-btn">${tweak.one_time ? "Run" : "Apply"}</button>
        `;
        card.querySelector(".apply-btn").addEventListener("click", (e) => handleTweakAction(tweak, e.target));
        return card;
    }

    function populateUI(data) {
        tweakGrid.innerHTML = '';
        mainNavList.innerHTML = '';

        const allTweaksItem = document.createElement('li');
        allTweaksItem.className = 'nav-item active';
        allTweaksItem.dataset.category = 'all';
        allTweaksItem.innerHTML = '<i class="fas fa-star"></i> All Tweaks';
        mainNavList.appendChild(allTweaksItem);

        for (const [category, tweaks] of Object.entries(data)) {
            const navItem = document.createElement('li');
            navItem.className = 'nav-item';
            navItem.dataset.category = category;
            navItem.innerHTML = `<i class="fas fa-cogs"></i> ${category.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}`;
            mainNavList.appendChild(navItem);

            tweaks.forEach(tweak => {
                const card = createTweakCard(tweak);
                card.dataset.category = category;
                tweakGrid.appendChild(card);
            });
        }
        document.querySelectorAll(".sidebar .nav-item").forEach(item => item.addEventListener("click", () => showPage(item.dataset.category)));
    }

    // --- State Management ---
    async function updateAllCardStates() {
        try {
            tweakStates = await window.pywebview.api.get_tweak_states();
            if (tweakStates) {
                document.querySelectorAll(".tweak-card[data-tweak-id]").forEach(updateCardUI);
            } else {
                showModal(false, "Fatal Error", "Could not load tweak states from backend.");
            }
        } catch (error) { showModal(false, "Initialization Error", "Could not fetch tweak states."); }
    }

    function updateCardUI(card) {
        const tweakId = card.dataset.tweakId;
        const state = tweakStates[tweakId];
        const button = card.querySelector(".apply-btn");
        const tweakData = findTweakById(tweakId);

        if (!button || !tweakData) return;

        if (tweakData.one_time) {
            card.classList.remove("applied");
            button.textContent = "Run"; button.disabled = false;
            button.title = `Run '${tweakData.title}'`;
            return;
        }

        if (state && state.is_applied) {
            card.classList.add("applied");
            button.textContent = "Revert";
            button.disabled = !state.can_revert;
            button.title = state.can_revert ? `Revert '${tweakData.title}'` : "Revert data not found.";
        } else {
            card.classList.remove("applied");
            button.textContent = "Apply";
            button.disabled = false;
            button.title = `Apply '${tweakData.title}'`;
        }
    }
    
    function findTweakById(tweakId) {
        for (const category of Object.values(tweaksData)) {
            const found = category.find(t => t.id === tweakId);
            if (found) return found;
        }
        return null;
    }

    // --- Actions & Event Handlers ---
    async function handleTweakAction(tweak, button) {
        if (tweak.warning && !confirm(`WARNING:\n\n${tweak.warning}\n\nDo you want to continue?`)) return;

        button.textContent = "Working..."; button.disabled = true;
        const card = button.closest(".tweak-card");
        const isApplied = card.classList.contains("applied");
        
        try {
            const result = isApplied ? await window.pywebview.api.revert_tweak(tweak.id) : await window.pywebview.api.apply_tweak(tweak.id);
            if (result.success) {
                showModal(true, "Success!", result.message);
                await updateAllCardStates();
            } else {
                showModal(false, "An Error Occurred", result.message);
                updateCardUI(card);
            }
        } catch (error) {
            showModal(false, "JavaScript Error", "Check console for details.");
            updateCardUI(card);
        }
    }

    function showPage(category) {
        document.querySelectorAll(".sidebar .nav-item").forEach(item => item.classList.remove("active"));
        document.querySelector(`.nav-item[data-category="${category}"]`)?.classList.add("active");

        pages.forEach(p => p.classList.add("hidden"));
        
        if (category === "analyzer") {
            document.getElementById("analyzer-page").classList.remove("hidden");
            runSystemAnalyzer();
        } else if (category === "gamemode") {
            document.getElementById("gamemode-page").classList.remove("hidden");
        } else {
            document.getElementById("tweaks-page").classList.remove("hidden");
            document.querySelectorAll(".tweak-card[data-tweak-id]").forEach(card => {
                card.style.display = (category === "all" || card.dataset.category === category) ? "flex" : "none";
            });
        }
    }

    async function runSystemAnalyzer() {
        recommendationsContainer.innerHTML = "<p>Analyzing your system for potential optimizations...</p>";
        const recommendations = await window.pywebview.api.get_system_analysis();
        recommendationsContainer.innerHTML = "";
        if (recommendations && recommendations.length > 0) {
            recommendations.forEach(tweak => {
                const card = createTweakCard(tweak);
                recommendationsContainer.appendChild(card);
            });
            await updateAllCardStates();
        } else {
            recommendationsContainer.innerHTML = "<p>No specific recommendations found. Your system looks well-configured!</p>";
        }
    }

    const showModal = (isSuccess, title, message) => {
        modalTitle.textContent = title;
        modalMessage.textContent = message;
        modalContent.classList.toggle("error", !isSuccess);
        modalIcon.className = isSuccess ? "fas fa-check-circle modal-icon-success" : "fas fa-times-circle modal-icon-error";
        feedbackModal.classList.add("visible");
    };

    const hideModal = () => feedbackModal.classList.remove("visible");

    closeAppBtn.addEventListener("click", () => window.pywebview.api.close_app());
    closeModalBtn.addEventListener("click", hideModal);
    feedbackModal.addEventListener("click", (e) => { if (e.target === feedbackModal) hideModal(); });

    // --- Frameless Window Resizing Logic ---
    const resizeHandles = document.querySelectorAll('[id^="resize-handle-"]');
    let resizeState = { resizing: false, direction: '', startPos: { x: 0, y: 0 } };
    resizeHandles.forEach(handle => { handle.addEventListener('mousedown', (e) => { e.preventDefault(); document.body.classList.add('is-resizing'); resizeState = { resizing: true, direction: handle.id.replace('resize-handle-', ''), startPos: { x: e.screenX, y: e.screenY }, startSize: { width: window.innerWidth, height: window.innerHeight }, startWinPos: { x: window.screenX, y: window.screenY } }; }); });
    document.addEventListener('mousemove', (e) => { if (resizeState.resizing) handleResize(e); });
    document.addEventListener('mouseup', () => { if (resizeState.resizing) { document.body.classList.remove('is-resizing'); resizeState.resizing = false; } });
    function handleResize(e) { const deltaX = e.screenX - resizeState.startPos.x; const deltaY = e.screenY - resizeState.startPos.y; let newWidth = resizeState.startSize.width; let newHeight = resizeState.startSize.height; let newX = resizeState.startWinPos.x; let newY = resizeState.startWinPos.y; const direction = resizeState.direction; if (direction.includes('E')) newWidth = resizeState.startSize.width + deltaX; if (direction.includes('W')) { newWidth = resizeState.startSize.width - deltaX; newX = resizeState.startWinPos.x + deltaX; } if (direction.includes('S')) newHeight = resizeState.startSize.height + deltaY; if (direction.includes('N')) { newHeight = resizeState.startSize.height - deltaY; newY = resizeState.startWinPos.y + deltaY; } const minWidth = 800, minHeight = 600; if (newWidth < minWidth) { if (direction.includes('W')) newX = resizeState.startWinPos.x + resizeState.startSize.width - minWidth; newWidth = minWidth; } if (newHeight < minHeight) { if (direction.includes('N')) newY = resizeState.startWinPos.y + resizeState.startSize.height - minHeight; newHeight = minHeight; } window.pywebview.api.reposition_window(newX, newY, newWidth, newHeight); }

    // --- Initial Load ---
    async function initialize() {
        try {
            tweaksData = await window.pywebview.api.get_tweaks();
            populateUI(tweaksData);
            await updateAllCardStates();
            showPage('all');
        } catch (error) {
            showModal(false, "Critical Error", "Could not load tweak data from Python backend.");
        }
    }
    initialize();
});