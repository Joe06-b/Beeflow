document.addEventListener("DOMContentLoaded", () => {
    const chartDataElement = document.getElementById("stock-chart-data");
    if (chartDataElement && window.Chart) {
        const chartData = JSON.parse(chartDataElement.textContent);
        const honey = "#d8a63a";
        const brown = "#76502b";
        const palette = ["#d8a63a", "#76502b", "#e7c76e", "#a7793d", "#4d3b2c", "#c08a4b", "#f0dca0"];
        const commonOptions = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
        };

        const quantitiesCanvas = document.getElementById("stockQuantitesChart");
        if (quantitiesCanvas) {
            new Chart(quantitiesCanvas, {
                type: "bar",
                data: { labels: chartData.quantites.labels, datasets: [{
                    label: "Quantité",
                    data: chartData.quantites.values,
                    backgroundColor: chartData.quantites.labels.map((_, i) => palette[i % palette.length]),
                    borderRadius: 7,
                    maxBarThickness: 48,
                }] },
                options: { ...commonOptions, scales: {
                    x: { grid: { display: false }, ticks: { color: brown } },
                    y: { beginAtZero: true, ticks: { color: brown }, grid: { color: "#f1ece4" } },
                } },
            });
        }

        const fillCanvas = document.getElementById("stockRemplissageChart");
        if (fillCanvas) {
            new Chart(fillCanvas, {
                type: "bar",
                data: { labels: chartData.remplissage.labels, datasets: [{
                    label: "Remplissage (%)",
                    data: chartData.remplissage.values,
                    backgroundColor: chartData.remplissage.values.map(value => value <= 25 ? "#c65c50" : honey),
                    borderRadius: 6,
                    maxBarThickness: 24,
                }] },
                options: { ...commonOptions, indexAxis: "y", scales: {
                    x: { min: 0, max: 100, ticks: { color: brown, callback: value => `${value}%` }, grid: { color: "#f1ece4" } },
                    y: { grid: { display: false }, ticks: { color: brown, autoSkip: false } },
                } },
            });
        }

        const locationsCanvas = document.getElementById("stockEmplacementsChart");
        if (locationsCanvas) {
            new Chart(locationsCanvas, {
                type: "doughnut",
                data: { labels: chartData.emplacements.labels, datasets: [{
                    data: chartData.emplacements.values,
                    backgroundColor: chartData.emplacements.labels.map((_, i) => palette[i % palette.length]),
                    borderColor: "#fff",
                    borderWidth: 3,
                }] },
                options: { ...commonOptions, cutout: "62%", plugins: {
                    legend: { position: "bottom", labels: { color: brown, usePointStyle: true, padding: 16 } },
                } },
            });
        }
    }

    const searchInput = document.getElementById("stockSearch");
    const filterSelect = document.getElementById("stockFilter");
    const productSelect = document.getElementById("stockProductFilter");
    const rows = Array.from(document.querySelectorAll("[data-stock-row]"));
    const noResults = document.getElementById("stockNoResults");
    const tableBody = document.getElementById("stockTableBody");
    const sortButtons = Array.from(document.querySelectorAll("[data-sort-key]"));

    if (!tableBody) return;

    let currentSortKey = "";
    let sortDirection = 1;

    const normalize = value => value
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .toLocaleLowerCase("fr");

    const updateRows = () => {
        const query = normalize(searchInput.value.trim());
        const state = filterSelect ? filterSelect.value : "all";
        const product = productSelect ? productSelect.value : "all";
        let visibleCount = 0;

        rows.forEach(row => {
            const matchesText = normalize(row.textContent).includes(query);
            const matchesState = state === "all" || row.dataset.state === state;
            const matchesProduct = product === "all" || row.dataset.product === product;
            const visible = matchesText && matchesState && matchesProduct;
            row.hidden = !visible;
            if (visible) visibleCount += 1;
        });

        if (noResults) noResults.hidden = visibleCount !== 0;
    };

    const sortRows = key => {
        if (currentSortKey === key) sortDirection *= -1;
        else {
            currentSortKey = key;
            sortDirection = 1;
        }

        const attribute = `sort${key[0].toUpperCase()}${key.slice(1)}`;
        rows.sort((left, right) => {
            const a = left.dataset[attribute] || "";
            const b = right.dataset[attribute] || "";
            const numeric = key === "quantity" || key === "fill";
            const comparison = numeric
                ? Number(a) - Number(b)
                : normalize(a).localeCompare(normalize(b), "fr");
            return comparison * sortDirection;
        });

        rows.forEach(row => tableBody.insertBefore(row, noResults));
        sortButtons.forEach(button => {
            const selected = button.dataset.sortKey === key;
            button.setAttribute("aria-pressed", selected ? "true" : "false");
            const indicator = button.querySelector("span");
            if (indicator) indicator.textContent = selected ? (sortDirection === 1 ? "↑" : "↓") : "↕";
        });
    };

    if (searchInput) searchInput.addEventListener("input", updateRows);
    if (filterSelect) filterSelect.addEventListener("change", updateRows);
    if (productSelect) productSelect.addEventListener("change", updateRows);
    sortButtons.forEach(button => button.addEventListener("click", () => sortRows(button.dataset.sortKey)));
});
