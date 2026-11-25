import { sceneWeather } from "./weather_state.js";

function assertEqual(actual, expected, message) {
    if (actual !== expected) {
        throw new Error(`${message}: expected ${expected}, received ${actual}`);
    }
}

export function runWeatherStateTests() {
    const data = {
        current: {
            time: "2026-11-21T04:00",
            wind_direction_degrees: 140,
            weather: { code: 3, category: "cloudy" },
        },
        hourly: [],
        daily: [],
    };
    const hourly = {
        time: "2026-11-21T05:00",
        wind_direction_degrees: null,
        weather: { code: 3, category: "cloudy" },
    };
    const forecast = sceneWeather(data, hourly, "2026-11-21", hourly.time);

    assertEqual(forecast.windDirectionDegrees, null, "Missing hourly direction");
    assertEqual(forecast.availability.windDirection.available, false, "Direction availability");
    assertEqual(forecast.availability.windDirection.provenance, "unavailable", "Direction provenance");
    assertEqual(forecast.provenance, "forecast", "Hourly provenance");
    assertEqual(forecast.daylightFactor, null, "Missing solar forecast");

    const observed = sceneWeather(data, data.current, "2026-11-21", data.current.time);
    assertEqual(observed.provenance, "observed", "Current provenance");
    assertEqual(observed.windDirectionDegrees, 140, "Observed wind direction");
    assertEqual(observed.availability.windDirection.provenance, "observed", "Observed direction provenance");

    const unavailable = sceneWeather(data, {
        time: "2026-11-21T06:00",
        weather: { code: null, description: null, category: "unknown" },
        temperature_c: null,
        relative_humidity_percent: null,
        wind_direction_degrees: null,
    }, "2026-11-21", "2026-11-21T06:00");
    assertEqual(unavailable.active, false, "All missing values remain inactive");
    assertEqual(unavailable.windDirectionDegrees, null, "Missing direction remains null");
    assertEqual(unavailable.availability.temperature.available, false, "Temperature availability");
    assertEqual(unavailable.availability.humidity.available, false, "Humidity availability");
    return true;
}
