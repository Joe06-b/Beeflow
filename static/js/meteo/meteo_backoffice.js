import { createMeteoScene } from "./scene.js";
import { csrfToken, fetchJson, withZoneId } from "./api.js";
import {
    formatDate,
    formatHour,
    formatRetrievedAt,
    formatValue,
} from "./format.js";
import {
    connectForecastUI,
    connectWeatherSimulation,
    showApiFailure,
} from "./forecast_ui.js";

const listRoot = document.querySelector("[data-meteo-backoffice-list]");
const detailRoot = document.querySelector("[data-meteo-backoffice-detail]");

function isValidCoordinates(zone) {
    return zone.latitude !== null
        && zone.latitude !== undefined
        && zone.latitude !== ""
        && zone.longitude !== null
        && zone.longitude !== undefined
        && zone.longitude !== ""
        && Number.isFinite(Number(zone.latitude))
        && Number.isFinite(Number(zone.longitude))
        && Number(zone.latitude) >= -90
        && Number(zone.latitude) <= 90
        && Number(zone.longitude) >= -180
        && Number(zone.longitude) <= 180;
}

function hasExpectedPrecipitation(data) {
    if (!data?.hourly?.length) return null;
    const now = data.current?.time || "";
    const upcoming = data.hourly.filter(row => row.time >= now);
    if (!upcoming.length) return null;
    const amounts = upcoming.map(row => row.precipitation_mm ?? row.rain_mm)
        .filter(value => value !== null && value !== undefined && Number.isFinite(Number(value)));
    if (!amounts.length) return null;
    return upcoming.some(row =>
        Number(row.rain_mm) > 0 || Number(row.precipitation_mm) > 0,
    );
}

function isWeatherVigilance(data) {
    const current = data?.current;
    if (current?.weather?.category === "storm") return true;
    if (current?.wind_speed_kmh !== null
        && current?.wind_speed_kmh !== undefined
        && Number(current.wind_speed_kmh) >= 50) return true;
    const now = current?.time || "";
    const nextDay = (data?.hourly || []).filter(row => row.time >= now).slice(0, 24);
    const values = nextDay.map(row => row.precipitation_mm ?? row.rain_mm)
        .filter(value => value !== null && value !== undefined && Number.isFinite(Number(value)));
    return values.length > 0 && values.reduce((sum, value) => sum + Number(value), 0) > 5;
}

function renderListPage(root) {
    const form = root.querySelector("[data-filter-form]");
    const body = root.querySelector("[data-zone-rows]");
    const countLabel = root.querySelector("[data-result-count]");
    const emptyState = root.querySelector("[data-empty-state]");
    const pagination = root.querySelector("[data-pagination]");
    const status = root.querySelector("[data-list-status]");
    const csrfForm = root.querySelector(".meteo-csrf");
    const reloadButton = root.querySelector("[data-reload-list]");
    const pageSize = 10;
    let rows = [];
    let currentPage = Number(new URLSearchParams(location.search).get("page")) || 1;
    let loadedCount = 0;
    let loadGeneration = 0;
    let loadController = null;
    const refreshControllers = new Set();

    function filterValue(name) {
        return form.querySelector(`[data-filter="${name}"]`)?.value || "";
    }

    const initialParams = new URLSearchParams(location.search);
    const queryNames = {
        sort: "tri",
        wind_min: "vent_min",
        wind_max: "vent_max",
        availability: "disponibilite",
    };
    form.querySelectorAll("[data-filter]").forEach(input => {
        const value = initialParams.get(queryNames[input.dataset.filter] || input.name);
        if (value !== null) input.value = value;
    });

    function filteredRows() {
        const query = filterValue("q").trim().toLocaleLowerCase("fr");
        const condition = filterValue("condition");
        const precipitation = filterValue("precipitation");
        const availability = filterValue("availability");
        const temperatureMin = filterValue("temperature_min");
        const temperatureMax = filterValue("temperature_max");
        const windMin = filterValue("wind_min");
        const windMax = filterValue("wind_max");

        return rows.filter(row => {
            const nameMatches = !query
                || row.zone.name.toLocaleLowerCase("fr").includes(query);
            if (!nameMatches) return false;

            if (availability === "gps" && isValidCoordinates(row.zone)) return false;
            if (availability === "available" && !row.data) return false;
            if (availability === "error" && !row.error) return false;
            if (
                condition === "unavailable"
                && (row.data || (!row.error && isValidCoordinates(row.zone)))
            ) return false;
            if (
                condition
                && condition !== "unavailable"
                && row.data?.current?.weather?.category !== condition
            ) return false;

            const hasRain = hasExpectedPrecipitation(row.data);
            if (precipitation === "yes" && hasRain !== true) return false;
            if (precipitation === "no" && hasRain !== false) return false;

            const temperature = row.data?.current?.temperature_c;
            const wind = row.data?.current?.wind_speed_kmh;
            if (temperatureMin !== "" && (
                temperature === null || temperature === undefined || !(temperature >= Number(temperatureMin))
            )) return false;
            if (temperatureMax !== "" && (
                temperature === null || temperature === undefined || !(temperature <= Number(temperatureMax))
            )) return false;
            if (windMin !== "" && (
                wind === null || wind === undefined || !(wind >= Number(windMin))
            )) return false;
            if (windMax !== "" && (
                wind === null || wind === undefined || !(wind <= Number(windMax))
            )) return false;
            return true;
        });
    }

    function sortedRows(items) {
        const sort = filterValue("sort") || "name";
        const compareValue = (left, right, key, direction = 1) => {
            const a = left.data?.current?.[key];
            const b = right.data?.current?.[key];
            if (a === null || a === undefined) return 1;
            if (b === null || b === undefined) return -1;
            return (Number(a) - Number(b)) * direction;
        };
        return [...items].sort((left, right) => {
            if (sort === "temperature_desc") return compareValue(left, right, "temperature_c", -1);
            if (sort === "temperature_asc") return compareValue(left, right, "temperature_c");
            if (sort === "wind_desc") return compareValue(left, right, "wind_speed_kmh", -1);
            if (sort === "condition") {
                return (left.data?.current?.weather?.description || "zzz")
                    .localeCompare(right.data?.current?.weather?.description || "zzz", "fr");
            }
            return left.zone.name.localeCompare(right.zone.name, "fr");
        });
    }

    function addCell(row, text, className = "") {
        const cell = document.createElement("td");
        if (className) cell.className = className;
        cell.textContent = text;
        row.append(cell);
        return cell;
    }

    function createRow(item) {
        const tr = document.createElement("tr");
        addCell(tr, String(item.zone.id), "num");

        const nameCell = document.createElement("td");
        const detail = document.createElement("a");
        detail.className = "env-zone-id";
        detail.href = withZoneId(root.dataset.detailUrlTemplate, item.zone.id);
        detail.textContent = item.zone.name;
        nameCell.append(detail);
        tr.append(nameCell);

        addCell(
            tr,
            isValidCoordinates(item.zone)
                ? `${Number(item.zone.latitude).toFixed(4)}, ${Number(item.zone.longitude).toFixed(4)}`
                : "Coordonnées invalides",
            "muted small",
        );

        const current = item.data?.current;
        addCell(tr, current ? formatValue(current.temperature_c, " °C") : "—");

        const conditionCell = document.createElement("td");
        const condition = document.createElement("span");
        condition.className = "badge";
        condition.textContent = current?.weather?.description
            || (item.error || !isValidCoordinates(item.zone) ? "Indisponible" : "Chargement…");
        conditionCell.append(condition);
        tr.append(conditionCell);

        const rain = hasExpectedPrecipitation(item.data);
        addCell(
            tr,
            rain === null
                ? "—"
                : rain
                    ? "Précipitations prévues"
                    : "Aucune prévue",
        );
        addCell(
            tr,
            current
                ? `${formatValue(current.wind_speed_kmh)} km/h`
                : "—",
        );

        addCell(
            tr,
            item.data ? formatRetrievedAt(item.data.retrieved_at) : "—",
            "muted small",
        );

        const stateCell = document.createElement("td");
        const state = document.createElement("span");
        state.className = `badge ${item.stale ? "meteo-badge-stale" : ""}`;
        if (item.stale) {
            state.textContent = "Anciennes données";
        } else if (item.data) {
            state.textContent = "Disponible";
            state.classList.add("meteo-badge-available");
        } else if (item.error?.code === "sans_coordonnees") {
            state.textContent = "GPS indisponible";
            state.classList.add("meteo-badge-unavailable");
        } else if (item.error) {
            state.textContent = "API indisponible";
            state.classList.add("meteo-badge-unavailable");
        } else if (!isValidCoordinates(item.zone)) {
            state.textContent = "GPS indisponible";
            state.classList.add("meteo-badge-unavailable");
        } else {
            state.textContent = "Chargement…";
        }
        stateCell.append(state);
        if (item.refreshError) {
            const note = document.createElement("small");
            note.className = "meteo-row-error";
            note.textContent = item.refreshError;
            stateCell.append(note);
        } else if (item.error?.message) {
            const note = document.createElement("small");
            note.className = "meteo-row-error";
            note.textContent = item.error.message;
            stateCell.append(note);
        }
        tr.append(stateCell);

        const actionCell = document.createElement("td");
        const actions = document.createElement("div");
        actions.className = "actions";
        const refresh = document.createElement("button");
        refresh.className = "icon-btn";
        refresh.type = "button";
        refresh.title = `Actualiser ${item.zone.name}`;
        refresh.setAttribute("aria-label", `Actualiser la météo de ${item.zone.name}`);
        refresh.textContent = "↻";
        refresh.disabled = !isValidCoordinates(item.zone);
        refresh.addEventListener("click", () => refreshZone(item, refresh));
        actions.append(refresh);
        const view = document.createElement("a");
        view.className = "icon-btn";
        view.href = detail.href;
        view.title = "Détail météo";
        view.setAttribute("aria-label", `Consulter la météo de ${item.zone.name}`);
        view.textContent = "→";
        actions.append(view);
        actionCell.append(actions);
        tr.append(actionCell);
        return tr;
    }

    function updateUrl(page = currentPage) {
        const params = new URLSearchParams();
        form.querySelectorAll("[data-filter]").forEach(input => {
            if (input.value) params.set(input.name, input.value);
        });
        if (page > 1) params.set("page", String(page));
        const query = params.toString();
        history.replaceState(null, "", `${location.pathname}${query ? `?${query}` : ""}`);
    }

    function renderPagination(pageCount) {
        pagination.replaceChildren();
        if (pageCount <= 1) return;

        const addButton = (label, page, disabled, current = false) => {
            const button = document.createElement("button");
            button.type = "button";
            button.className = current ? "is-current" : "";
            button.textContent = label;
            button.disabled = disabled;
            if (current) button.setAttribute("aria-current", "page");
            button.addEventListener("click", () => {
                currentPage = page;
                updateUrl(page);
                render();
            });
            pagination.append(button);
        };

        addButton("‹", Math.max(1, currentPage - 1), currentPage <= 1);
        const first = Math.max(1, currentPage - 2);
        const last = Math.min(pageCount, currentPage + 2);
        for (let page = first; page <= last; page += 1) {
            addButton(String(page), page, false, page === currentPage);
        }
        addButton("›", Math.min(pageCount, currentPage + 1), currentPage >= pageCount);
    }

    function render() {
        const items = sortedRows(filteredRows());
        const pageCount = Math.max(1, Math.ceil(items.length / pageSize));
        currentPage = Math.min(currentPage, pageCount);
        const visible = items.slice((currentPage - 1) * pageSize, currentPage * pageSize);
        body.replaceChildren(...visible.map(createRow));
        countLabel.textContent = `${items.length} zone${items.length > 1 ? "s" : ""}${items.length ? ` · page ${currentPage} sur ${pageCount}` : ""}`;
        emptyState.hidden = items.length > 0;
        pagination.hidden = items.length === 0;
        renderPagination(pageCount);
    }

    function updateKpis() {
        const withCoordinates = rows.filter(row => isValidCoordinates(row.zone));
        const available = rows.filter(row => row.data);
        const rainCount = available.filter(row => hasExpectedPrecipitation(row.data) === true).length;
        const averageFor = key => {
            const values = available.map(row => row.data.current[key])
                .filter(value => value !== null && value !== undefined && Number.isFinite(Number(value)));
            return values.length
                ? formatValue(values.reduce((sum, value) => sum + Number(value), 0) / values.length, key === "temperature_c" ? " °C" : " %")
                : "—";
        };
        const vigilanceCount = available.filter(row => isWeatherVigilance(row.data)).length;
        root.querySelector('[data-kpi="total"]').textContent = String(withCoordinates.length);
        root.querySelector('[data-kpi="available"]').textContent = String(available.length);
        root.querySelector('[data-kpi="rain"]').textContent = String(rainCount);
        root.querySelector('[data-kpi="temperature"]').textContent = averageFor("temperature_c");
        root.querySelector('[data-kpi="humidity"]').textContent = averageFor("relative_humidity_percent");
        root.querySelector('[data-kpi="vigilance"]').textContent = String(vigilanceCount);
    }

    async function refreshZone(item, button) {
        const generation = loadGeneration;
        const controller = new AbortController();
        refreshControllers.add(controller);
        button.disabled = true;
        item.refreshError = "";
        try {
            const url = withZoneId(root.dataset.refreshUrlTemplate, item.zone.id);
            item.data = await fetchJson(url, {
                method: "POST",
                headers: { "X-CSRFToken": csrfToken(csrfForm) },
                signal: controller.signal,
            });
            if (generation !== loadGeneration) return;
            item.error = null;
            item.stale = false;
            item.refreshError = "";
            status.textContent = `Prévisions actualisées pour ${item.zone.name}.`;
        } catch (error) {
            if (error.name === "AbortError" || generation !== loadGeneration) return;
            item.stale = Boolean(item.data);
            item.refreshError = error.message || "Actualisation indisponible.";
            status.textContent = `${item.zone.name} : ${item.refreshError}`;
        } finally {
            refreshControllers.delete(controller);
        }
        if (generation !== loadGeneration) return;
        render();
        button.disabled = !isValidCoordinates(item.zone);
    }

    async function loadRows() {
        const generation = ++loadGeneration;
        loadController?.abort();
        refreshControllers.forEach(controller => controller.abort());
        refreshControllers.clear();
        const controller = new AbortController();
        loadController = controller;
        loadedCount = 0;
        reloadButton.disabled = true;
        status.textContent = "Chargement des zones…";
        body.replaceChildren();
        try {
            const payload = await fetchJson(root.dataset.zonesUrl, {
                signal: controller.signal,
            });
            if (generation !== loadGeneration) return;
            rows = payload.zones.map(zone => ({ zone, data: null, error: null }));
            updateKpis();
            render();

            const pending = rows.filter(row => isValidCoordinates(row.zone));
            const concurrency = Math.min(3, pending.length);
            let nextIndex = 0;
            const worker = async () => {
                while (nextIndex < pending.length) {
                    const item = pending[nextIndex++];
                    try {
                        const url = withZoneId(root.dataset.weatherUrlTemplate, item.zone.id);
                        item.data = await fetchJson(url, { signal: controller.signal });
                    } catch (error) {
                        if (error.name === "AbortError") return;
                        item.error = error;
                    }
                    loadedCount += 1;
                    if (generation !== loadGeneration) return;
                    updateKpis();
                    render();
                    status.textContent = `Prévisions récupérées pour ${loadedCount} sur ${pending.length} zone${pending.length > 1 ? "s" : ""}.`;
                }
            };
            await Promise.all(Array.from({ length: concurrency }, worker));
            if (generation === loadGeneration) {
                status.textContent = rows.length
                    ? "État météo et horodatages mis à jour."
                    : "Aucune zone environnementale n'est enregistrée.";
            }
        } catch (error) {
            if (error.name === "AbortError") return;
            if (generation === loadGeneration) status.textContent = error.message;
        } finally {
            if (generation === loadGeneration) {
                loadController = null;
                reloadButton.disabled = false;
            }
        }
    }

    form.addEventListener("submit", event => {
        event.preventDefault();
        currentPage = 1;
        updateUrl(1);
        render();
    });
    form.querySelectorAll("[data-filter]").forEach(input => {
        input.addEventListener("change", () => {
            currentPage = 1;
            updateUrl(1);
            render();
        });
    });
    form.querySelector('[data-filter="q"]').addEventListener("input", () => {
        currentPage = 1;
        updateUrl(1);
        render();
    });
    reloadButton.addEventListener("click", loadRows);
    window.addEventListener("pagehide", () => {
        loadController?.abort();
        refreshControllers.forEach(controller => controller.abort());
    }, { once: true });
    loadRows();
}

function renderDetailPage(root) {
    const scene = createMeteoScene(root.querySelector("[data-meteo-scene]"), {
        debug: root.dataset.meteoSimulations === "true",
    });
    const simulation = connectWeatherSimulation(root, scene);
    const refresh = root.querySelector("[data-refresh]");
    const csrfForm = root.querySelector(".meteo-csrf");
    const status = root.querySelector("[data-status]");
    const dataUrl = root.dataset.weatherUrl;
    let requestNumber = 0;
    let weatherController = null;

    async function loadWeather(force = false) {
        const currentRequest = ++requestNumber;
        weatherController?.abort();
        const controller = new AbortController();
        weatherController = controller;
        if (refresh) refresh.disabled = true;
        status.textContent = force ? "Actualisation des prévisions…" : "Chargement des prévisions…";
        try {
            const data = force
                ? await fetchJson(root.dataset.refreshUrl, {
                    method: "POST",
                    headers: { "X-CSRFToken": csrfToken(csrfForm) },
                    signal: controller.signal,
                })
                : await fetchJson(dataUrl, { signal: controller.signal });
            if (currentRequest !== requestNumber) return;
            connectForecastUI(root, data, scene, simulation);
            status.textContent = `Données disponibles pour ${data.zone.name}.`;
        } catch (error) {
            if (error.name === "AbortError" || currentRequest !== requestNumber) return;
            showApiFailure(root, error, scene, simulation);
            status.textContent = error.message || "Les données météo sont indisponibles.";
        } finally {
            if (currentRequest === requestNumber) {
                weatherController = null;
                if (refresh) refresh.disabled = false;
            }
        }
    }

    refresh.addEventListener("click", () => loadWeather(true));
    window.addEventListener("pagehide", () => weatherController?.abort(), {
        once: true,
    });
    loadWeather();
}

if (listRoot) renderListPage(listRoot);
if (detailRoot) renderDetailPage(detailRoot);
