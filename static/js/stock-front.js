document.addEventListener("DOMContentLoaded", () => {
    const cards = Array.from(document.querySelectorAll("[data-stock-front-row]"));
    const search = document.getElementById("frontStockSearch");
    const productFilter = document.getElementById("frontStockProductFilter");
    const statusFilter = document.getElementById("frontStockStatusFilter");
    const sortSelect = document.getElementById("frontStockSort");
    const recordsContainer = document.querySelector(".stock-front-records");
    const noResults = document.getElementById("frontStockNoResults");
    const countOutput = document.getElementById("frontStockRowsCount");
    const alertsOutput = document.getElementById("frontStockAlertsCount");
    const fillOutput = document.getElementById("frontStockFillAverage");

    const normalize = value => (value || "")
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .toLocaleLowerCase("fr");

    const applyStockFilters = () => {
        if (!cards.length) return;
        const query = normalize(search?.value.trim());
        const selectedProduct = productFilter?.value || "all";
        const selectedState = statusFilter?.value || "all";
        const sortBy = sortSelect?.value || "product";
        const sortAttribute = {
            product: "product",
            quantity: "quantity",
            fill: "fill",
            location: "location",
        }[sortBy] || "product";

        const visibleCards = [];
        cards.forEach(card => {
            const visible = normalize(card.textContent).includes(query)
                && (selectedProduct === "all" || card.dataset.product === selectedProduct)
                && (selectedState === "all" || card.dataset.state === selectedState);
            card.hidden = !visible;
            if (visible) visibleCards.push(card);
        });

        visibleCards.sort((left, right) => {
            if (sortAttribute === "quantity" || sortAttribute === "fill") {
                return Number(left.dataset[sortAttribute] || 0) - Number(right.dataset[sortAttribute] || 0);
            }
            return normalize(left.dataset[sortAttribute]).localeCompare(normalize(right.dataset[sortAttribute]), "fr");
        });
        visibleCards.forEach(card => recordsContainer.appendChild(card));

        const visibleAlerts = visibleCards.filter(card => card.dataset.state !== "disponible").length;
        const averageFill = visibleCards.length
            ? visibleCards.reduce((total, card) => total + Number(card.dataset.fill || 0), 0) / visibleCards.length
            : 0;

        if (countOutput) countOutput.textContent = String(visibleCards.length);
        if (alertsOutput) alertsOutput.textContent = String(visibleAlerts);
        if (fillOutput) fillOutput.textContent = `${averageFill.toFixed(1)}%`;
        if (noResults) noResults.hidden = visibleCards.length > 0;
    };

    [search, productFilter, statusFilter, sortSelect].forEach(control => {
        if (control) control.addEventListener(control === search ? "input" : "change", applyStockFilters);
    });
    applyStockFilters();

    const quantityInput = document.getElementById("id_quantite");
    const capacityInput = document.getElementById("id_capacite_max");
    const thresholdInput = document.getElementById("id_seuil_alerte");
    const percentOutput = document.getElementById("frontPreviewPercent");
    const statusOutput = document.getElementById("frontPreviewStatus");
    const descriptionOutput = document.getElementById("frontPreviewDescription");
    const progressTrack = document.querySelector(".stock-form-preview-track");
    const progressBar = document.getElementById("frontPreviewBar");

    if (!quantityInput || !capacityInput || !thresholdInput || !progressBar) return;

    const updatePreview = () => {
        const quantity = Number(quantityInput.value);
        const capacity = Number(capacityInput.value);
        const threshold = Number(thresholdInput.value);
        const hasQuantity = quantityInput.value !== "" && Number.isFinite(quantity);
        const hasCapacity = capacityInput.value !== "" && Number.isFinite(capacity) && capacity > 0;
        const hasThreshold = thresholdInput.value !== "" && Number.isFinite(threshold);

        if (!hasQuantity || !hasCapacity) {
            if (percentOutput) percentOutput.textContent = "--%";
            if (statusOutput) statusOutput.textContent = "Saisissez les quantites";
            if (descriptionOutput) descriptionOutput.textContent = "Ajoutez une quantite et une capacite pour voir le niveau.";
            progressBar.style.width = "0%";
            progressTrack?.setAttribute("aria-valuenow", "0");
            return;
        }

        const percent = Math.max(0, Math.min(100, (quantity / capacity) * 100));
        const roundedPercent = Math.round(percent * 10) / 10;
        const state = quantity <= 0 ? "epuise" : (hasThreshold && quantity <= threshold ? "bientot_epuise" : "disponible");
        const stateLabels = {
            disponible: "Disponible",
            bientot_epuise: "Bientot epuise",
            epuise: "Epuise",
        };

        if (percentOutput) percentOutput.textContent = `${roundedPercent}%`;
        if (statusOutput) statusOutput.textContent = stateLabels[state];
        if (descriptionOutput) descriptionOutput.textContent = `${quantityInput.value} sur ${capacityInput.value} en capacite maximale`;
        progressBar.style.width = `${roundedPercent}%`;
        progressBar.classList.toggle("is-low", state !== "disponible");
        progressTrack?.setAttribute("aria-valuenow", String(roundedPercent));
    };

    [quantityInput, capacityInput, thresholdInput].forEach(input => input.addEventListener("input", updatePreview));
    updatePreview();
});
