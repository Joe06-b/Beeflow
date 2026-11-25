import {
    formatDate,
    formatHour,
    formatRetrievedAt,
    formatValue,
} from "./format.js";
import { sceneWeather, weatherForSelectedTime } from "./weather_state.js";

const SIMULATION_SCENARIOS = {
    sunny: {
        label: "Soleil",
        state: {
            category: "clear",
            cloudCover: 0,
            precipitation: 0,
            rain: 0,
            daylightFactor: 1,
            twilightFactor: 0,
            solarProgress: 0.5,
        },
    },
    partly_cloudy: {
        label: "Ciel partiellement nuageux",
        state: {
            category: "cloudy",
            cloudCover: 48,
            precipitation: 0,
            rain: 0,
            daylightFactor: 0.76,
            twilightFactor: 0.68,
            solarProgress: 0.5,
        },
    },
    overcast: {
        label: "Ciel couvert",
        state: {
            category: "cloudy",
            cloudCover: 96,
            precipitation: 0,
            rain: 0,
            daylightFactor: 0.46,
            twilightFactor: 0.98,
            solarProgress: 0.5,
        },
    },
    fog: {
        label: "Brouillard",
        state: {
            category: "fog",
            cloudCover: null,
            precipitation: null,
            rain: null,
            daylightFactor: 0.58,
            twilightFactor: 0.82,
            solarProgress: 0.5,
        },
    },
    light_rain: {
        label: "Pluie légère",
        state: {
            category: "rain",
            cloudCover: 82,
            precipitation: 0.5,
            rain: 0.5,
            windSpeed: 8,
            daylightFactor: 0.48,
            twilightFactor: 0.94,
            solarProgress: 0.5,
        },
    },
    heavy_rain: {
        label: "Pluie forte",
        state: {
            category: "rain",
            cloudCover: 100,
            precipitation: 8,
            rain: 8,
            windSpeed: 20,
            daylightFactor: 0.3,
            twilightFactor: 0.92,
            solarProgress: 0.5,
        },
    },
    storm: {
        label: "Orage avec éclairs",
        state: {
            category: "storm",
            cloudCover: 100,
            precipitation: 8,
            rain: 8,
            windSpeed: 28,
            daylightFactor: 0.22,
            twilightFactor: 0.88,
            solarProgress: 0.5,
        },
    },
    night: {
        label: "Nuit",
        state: {
            category: "unknown",
            cloudCover: null,
            precipitation: 0,
            rain: 0,
            isNight: true,
            daylightFactor: 0,
            twilightFactor: 0,
            solarProgress: 0.5,
        },
    },
    snow: {
        label: "Neige",
        state: {
            category: "snow",
            cloudCover: 92,
            precipitation: 1.5,
            rain: 0,
            windSpeed: 12,
            daylightFactor: 0.62,
            twilightFactor: 0.55,
            solarProgress: 0.5,
        },
    },
};

export function connectWeatherSimulation(root, scene) {
    const select = root.querySelector("[data-simulation-select]");
    if (!select || root.dataset.meteoSimulations !== "true") return null;

    const banner = root.querySelector("[data-simulation-banner]");
    const caption = root.querySelector("[data-scene-caption-text]");
    let forecastState = { active: false };
    let forecastCaption = caption?.textContent || "";

    function apply() {
        const simulation = SIMULATION_SCENARIOS[select.value];
        if (!simulation) {
            if (banner) banner.hidden = true;
            if (caption) caption.textContent = forecastCaption;
            scene.setWeather(forecastState);
            return;
        }

        if (banner) {
            banner.hidden = false;
            banner.textContent = "Simulation visuelle uniquement : les prévisions et les valeurs affichées ne sont pas modifiées.";
        }
        if (caption) caption.textContent = `SIMULATION DEBUG · ${simulation.label}`;
        scene.setWeather({
            active: true,
            isSimulation: true,
            provenance: "simulation",
            ...simulation.state,
        });
    }

    select.addEventListener("change", apply);
    return {
        setForecastState(state, text) {
            forecastState = state || { active: false };
            if (typeof text === "string") forecastCaption = text;
            apply();
        },
    };
}

function setValue(root, name, value) {
    root.querySelectorAll(`[data-value="${name}"]`).forEach(element => {
        element.textContent = value;
    });
}

function forecastLabel(row) {
    return row.weather?.description || "Condition indisponible";
}

function selectedForecastValue(selected, daily) {
    if (!selected) return null;
    return {
        temperature: selected.temperature_c ?? selected.temperature_max_c,
        apparent: selected.apparent_temperature_c,
        humidity: selected.relative_humidity_percent,
        wind: selected.wind_speed_kmh ?? selected.wind_speed_max_kmh,
        gusts: selected.wind_gusts_kmh,
        precipitation: selected.precipitation_mm ?? selected.precipitation_sum_mm,
        clouds: selected.cloud_cover_percent,
        direction: selected.wind_direction_degrees,
        pressure: selected.surface_pressure_hpa,
        visibility: selected.visibility_m,
        uv: selected.uv_index ?? daily?.uv_index_max,
        probability: selected.precipitation_probability_percent
            ?? daily?.precipitation_probability_percent,
    };
}

export function connectForecastUI(root, data, scene, simulation = null) {
    root._meteoForecastUI?.dispose();
    const daySelect = root.querySelector("[data-day-select]");
    const hourSelect = root.querySelector("[data-hour-select]");
    const dayList = root.querySelector("[data-day-list]");
    const status = root.querySelector("[data-status]");
    const timezoneLabel = root.querySelector("[data-timezone]");
    const updatedLabel = root.querySelector("[data-updated]");
    const caption = root.querySelector("[data-scene-caption-text]");
    const selectedDayLabel = root.querySelector("[data-selected-day-label]");
    const provenanceLabel = root.querySelector("[data-weather-provenance]");
    scene.setZone?.(data.zone);
    const today = data.current?.time?.slice(0, 10);
    const initialDay = data.daily?.some(row => row.time === today)
        ? today
        : data.daily?.[0]?.time || "";
    let activeDay = initialDay;
    let activeHour = "";

    if (timezoneLabel) timezoneLabel.textContent = data.timezone || "Fuseau horaire indisponible";
    if (updatedLabel) updatedLabel.textContent = formatRetrievedAt(data.retrieved_at);
    if (daySelect) {
        daySelect.replaceChildren();
        (data.daily || []).forEach(row => {
            const option = document.createElement("option");
            option.value = row.time;
            option.textContent = formatDate(row.time, { short: true });
            daySelect.append(option);
        });
        daySelect.disabled = !data.daily?.length;
        daySelect.value = initialDay;
    }

    function renderDayCards() {
        if (!dayList) return;
        dayList.replaceChildren();
        (data.daily || []).forEach(row => {
            const button = document.createElement("button");
            button.type = "button";
            button.className = "meteo-day-card";
            button.dataset.day = row.time;
            button.setAttribute("aria-pressed", String(row.time === activeDay));

            const date = document.createElement("span");
            date.className = "meteo-day-date";
            date.textContent = formatDate(row.time, { short: true });
            const description = document.createElement("strong");
            description.textContent = forecastLabel(row);
            const temperatures = document.createElement("span");
            temperatures.className = "meteo-day-temperatures";
            temperatures.textContent = `${formatValue(row.temperature_min_c, "°")} / ${formatValue(row.temperature_max_c, "°")}`;
            const probability = document.createElement("span");
            probability.className = "meteo-day-probability";
            probability.textContent = row.precipitation_probability_percent === null
                || row.precipitation_probability_percent === undefined
                ? "Probabilité indisponible"
                : `${formatValue(row.precipitation_probability_percent, "%")} de pluie`;
            const precipitation = document.createElement("span");
            precipitation.className = "meteo-day-probability";
            precipitation.textContent = row.precipitation_sum_mm === null
                || row.precipitation_sum_mm === undefined
                ? "Précipitations indisponibles"
                : `${formatValue(row.precipitation_sum_mm, " mm")} prévues`;
            button.append(date, description, temperatures, probability, precipitation);
            button.addEventListener("click", () => selectDay(row.time));
            dayList.append(button);
        });
    }

    function fillHours(day) {
        if (!hourSelect) return;
        const hours = (data.hourly || []).filter(row => row.time.slice(0, 10) === day);
        hourSelect.replaceChildren();
        hours.forEach(row => {
            const option = document.createElement("option");
            option.value = row.time;
            const isCurrentHour = row.time.slice(0, 13) === data.current?.time?.slice(0, 13);
            option.textContent = `${formatHour(row.time)}${isCurrentHour ? " · maintenant" : ""}`;
            hourSelect.append(option);
        });

        const currentHour = hours.find(row =>
            row.time.slice(0, 13) === data.current?.time?.slice(0, 13),
        );
        const latestAvailableHour = hours.filter(row => row.time <= (data.current?.time || ""))
            .pop();
        activeHour = currentHour?.time || latestAvailableHour?.time || hours[0]?.time || "";
        hourSelect.disabled = hours.length === 0;
        if (hours.length) hourSelect.value = activeHour;
    }

    function updateView() {
        const daily = data.daily?.find(row => row.time === activeDay) || null;
        const selected = weatherForSelectedTime(data, activeDay, activeHour);
        const isCurrentHour = Boolean(
            selected
            && activeHour
            && activeHour.slice(0, 13) === data.current?.time?.slice(0, 13),
        );
        const displayed = isCurrentHour ? data.current : selected;
        const values = selectedForecastValue(displayed, daily);
        const state = sceneWeather(data, displayed || daily, activeDay, activeHour);

        setValue(root, "temperature", formatValue(values?.temperature));
        setValue(root, "apparent", formatValue(values?.apparent, " °C"));
        setValue(root, "humidity", formatValue(values?.humidity, " %"));
        setValue(root, "wind", formatValue(values?.wind, " km/h"));
        setValue(root, "gusts", formatValue(values?.gusts, " km/h"));
        setValue(root, "precipitation", formatValue(values?.precipitation, " mm"));
        setValue(root, "clouds", formatValue(values?.clouds, " %"));
        setValue(root, "direction", formatValue(values?.direction, "°"));
        setValue(root, "pressure", formatValue(values?.pressure, " hPa"));
        setValue(root, "visibility", formatValue(
            values?.visibility === null || values?.visibility === undefined
                ? null
                : values.visibility / 1000,
            " km",
        ));
        setValue(root, "uv", formatValue(values?.uv));
        setValue(root, "probability", formatValue(values?.probability, " %"));

        root.querySelectorAll("[data-weather-description]").forEach(element => {
            element.textContent = forecastLabel(displayed || daily || {});
        });
        const dayLabel = formatDate(activeDay, { short: true });
        if (caption) {
            caption.textContent = `${dayLabel}${activeHour ? ` · ${formatHour(activeHour)}` : ""} · ${forecastLabel(displayed || daily || {})}`;
        }
        if (selectedDayLabel) selectedDayLabel.textContent = `${dayLabel} · AU RUCHER`;
        if (provenanceLabel) {
            provenanceLabel.textContent = !state?.active
                ? "DONNÉES INDISPONIBLES"
                : state.provenance === "observed"
                    ? "OBSERVATION ACTUELLE"
                    : "PRÉVISION";
        }
        if (status) {
            const detail = `${formatDate(activeDay)}${activeHour ? ` à ${formatHour(activeHour)}` : ""}`;
            status.textContent = state?.provenance === "observed"
                ? `Observation du ${detail} · fuseau ${data.timezone || "inconnu"}.`
                : selected
                    ? `Prévisions du ${detail} · fuseau ${data.timezone || "inconnu"}.`
                    : `Prévisions journalières du ${formatDate(activeDay)}.`;
        }

        if (simulation) {
            simulation.setForecastState(state || { active: false }, caption?.textContent);
        } else {
            scene.setWeather(state || { active: false });
        }
        renderDayCards();
    }

    function selectDay(day) {
        if (!day) return;
        activeDay = day;
        if (daySelect) daySelect.value = day;
        fillHours(day);
        updateView();
    }

    const onDayChange = () => selectDay(daySelect.value);
    const onHourChange = () => {
        activeHour = hourSelect.value;
        updateView();
    };
    daySelect?.addEventListener("change", onDayChange);
    hourSelect?.addEventListener("change", onHourChange);

    fillHours(initialDay);
    renderDayCards();
    updateView();
    const controller = {
        selectDay,
        dispose() {
            daySelect?.removeEventListener("change", onDayChange);
            hourSelect?.removeEventListener("change", onHourChange);
        },
    };
    root._meteoForecastUI = controller;
    return controller;
}

export function showApiFailure(root, error, scene, simulation = null) {
    const status = root.querySelector("[data-status]");
    if (status) status.textContent = error.message || "Les données météo sont indisponibles.";
    root.querySelectorAll("[data-value]").forEach(element => {
        element.textContent = "—";
    });
    root.querySelectorAll("[data-weather-description]").forEach(element => {
        element.textContent = "Conditions indisponibles";
    });
    if (simulation) simulation.setForecastState({ active: false });
    else scene?.setWeather({ active: false });
}
