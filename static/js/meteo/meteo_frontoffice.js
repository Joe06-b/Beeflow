import { createMeteoScene } from "./scene.js";
import { fetchJson, csrfToken, withZoneId } from "./api.js";
import {
    connectForecastUI,
    connectWeatherSimulation,
    showApiFailure,
} from "./forecast_ui.js";

const root = document.querySelector("[data-meteo-frontoffice]");
if (root) {
    const zoneSelect = root.querySelector("[data-zone-select]");
    const refreshButton = root.querySelector("[data-refresh]");
    const refreshForm = root.querySelector(".meteo-csrf");
    const status = root.querySelector("[data-status]");
    const scene = createMeteoScene(root.querySelector("[data-meteo-scene]"), {
        debug: root.dataset.meteoSimulations === "true",
    });
    const simulation = connectWeatherSimulation(root, scene);
    let zones = [];
    let activeZoneId = "";
    let requestNumber = 0;
    let weatherController = null;
    let zonesController = null;

    function setStatus(message) {
        if (status) status.textContent = message;
    }

    function setZoneControls(enabled) {
        if (zoneSelect) zoneSelect.disabled = !enabled;
        if (refreshButton) refreshButton.disabled = !enabled;
    }

    async function loadWeather(zoneId) {
        if (!zoneId) return;
        const currentRequest = ++requestNumber;
        weatherController?.abort();
        const controller = new AbortController();
        weatherController = controller;
        activeZoneId = zoneId;
        const selectedZone = zones.find(zone => String(zone.id) === String(zoneId));
        if (selectedZone) {
            scene.setZone?.(selectedZone);
            root.querySelectorAll("[data-zone-name]").forEach(element => {
                element.textContent = selectedZone.name;
            });
        }
        setZoneControls(false);
        root.querySelector("[data-day-select]").disabled = true;
        root.querySelector("[data-hour-select]").disabled = true;
        setStatus("Récupération des prévisions de la zone…");
        try {
            const url = withZoneId(root.dataset.weatherUrlTemplate, zoneId);
            const data = await fetchJson(url, { signal: controller.signal });
            if (currentRequest !== requestNumber || zoneSelect.value !== zoneId) return;
            root.querySelectorAll("[data-zone-name]").forEach(element => {
                element.textContent = data.zone.name;
            });
            connectForecastUI(root, data, scene, simulation);
            setStatus(`Données météo disponibles pour ${data.zone.name}.`);
        } catch (error) {
            if (error.name === "AbortError") return;
            if (currentRequest !== requestNumber) return;
            showApiFailure(root, error, scene, simulation);
            setStatus(error.message);
        } finally {
            if (currentRequest === requestNumber) {
                weatherController = null;
                setZoneControls(Boolean(zoneId));
            }
        }
    }

    async function loadZones() {
        const controller = new AbortController();
        zonesController = controller;
        try {
            const payload = await fetchJson(root.dataset.zonesUrl, {
                signal: controller.signal,
            });
            zones = payload.zones;
            zoneSelect.replaceChildren();
            zones.forEach(zone => {
                const option = document.createElement("option");
                option.value = String(zone.id);
                option.textContent = zone.name;
                zoneSelect.append(option);
            });
            if (!zones.length) {
                const option = document.createElement("option");
                option.value = "";
                option.textContent = "Aucune zone enregistrée";
                zoneSelect.append(option);
                setStatus("Aucune zone environnementale n'est enregistrée.");
                return;
            }
            zoneSelect.value = String(payload.zones[0].id);
            await loadWeather(zoneSelect.value);
        } catch (error) {
            if (error.name === "AbortError") return;
            setStatus(error.message || "Impossible de charger la liste des zones.");
            const option = document.createElement("option");
            option.value = "";
            option.textContent = "Zones indisponibles";
            zoneSelect.replaceChildren(option);
        }
    }

    zoneSelect.addEventListener("change", () => loadWeather(zoneSelect.value));
    refreshButton.addEventListener("click", async () => {
        if (!activeZoneId) return;
        const zoneId = activeZoneId;
        const currentRequest = ++requestNumber;
        weatherController?.abort();
        const controller = new AbortController();
        weatherController = controller;
        refreshButton.disabled = true;
        setStatus("Actualisation des prévisions…");
        try {
            const url = withZoneId(root.dataset.refreshUrlTemplate, zoneId);
            const data = await fetchJson(url, {
                method: "POST",
                headers: { "X-CSRFToken": csrfToken(refreshForm) },
                signal: controller.signal,
            });
            if (currentRequest !== requestNumber || zoneSelect.value !== zoneId) return;
            root.querySelectorAll("[data-zone-name]").forEach(element => {
                element.textContent = data.zone.name;
            });
            connectForecastUI(root, data, scene, simulation);
            setStatus(`Prévisions actualisées pour ${data.zone.name}.`);
        } catch (error) {
            if (error.name === "AbortError") return;
            if (currentRequest === requestNumber) {
                setStatus(error.message || "L'actualisation a échoué.");
            }
        } finally {
            if (currentRequest === requestNumber) {
                weatherController = null;
                refreshButton.disabled = false;
            }
        }
    });

    window.addEventListener("pagehide", () => {
        weatherController?.abort();
        zonesController?.abort();
    }, { once: true });

    loadZones();
}
