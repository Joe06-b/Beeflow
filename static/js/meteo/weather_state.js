function toMinutes(value) {
    if (typeof value !== "string") return null;
    const match = value.match(/T?(\d{2}):(\d{2})/);
    return match ? Number(match[1]) * 60 + Number(match[2]) : null;
}

function smoothstep(start, end, value) {
    const amount = Math.max(0, Math.min(1, (value - start) / (end - start)));
    return amount * amount * (3 - 2 * amount);
}

function fieldAvailability(value, provenance) {
    const available = value !== null && value !== undefined;
    return {
        available,
        provenance: available ? provenance : "unavailable",
    };
}

function solarState(time, daily, current) {
    const hour = toMinutes(time?.slice(11, 16));
    const sunrise = toMinutes(daily?.sunrise?.slice(11, 16));
    const sunset = toMinutes(daily?.sunset?.slice(11, 16));

    if (
        hour !== null
        && sunrise !== null
        && sunset !== null
        && sunset > sunrise
    ) {
        const daylightFactor = smoothstep(sunrise - 50, sunrise + 30, hour)
            * (1 - smoothstep(sunset - 30, sunset + 55, hour));
        const matchesCurrentHour = current?.time?.slice(0, 13) === time.slice(0, 13);
        const isNight = matchesCurrentHour && Number.isInteger(current?.is_day)
            ? current.is_day === 0
            : daylightFactor < 0.08;
        return {
            isNight,
            daylightFactor,
            twilightFactor: Math.sin(Math.PI * daylightFactor),
            solarProgress: Math.max(
                0,
                Math.min(1, (hour - sunrise) / (sunset - sunrise)),
            ),
            provenance: "forecast",
        };
    }

    const matchesCurrentHour = Boolean(
        time
        && current?.time?.slice(0, 13) === time.slice(0, 13)
        && Number.isInteger(current?.is_day),
    );
    if (matchesCurrentHour) {
        const isNight = current.is_day === 0;
        return {
            isNight,
            daylightFactor: isNight ? 0 : 1,
            twilightFactor: null,
            solarProgress: null,
            provenance: "observed",
        };
    }

    return {
        isNight: null,
        daylightFactor: null,
        twilightFactor: null,
        solarProgress: null,
        provenance: "unavailable",
    };
}

export function weatherForSelectedTime(data, date, time) {
    if (!data) return null;
    if (time && data.current?.time === time) return data.current;
    if (time) {
        const hour = data.hourly?.find(row => row.time === time);
        if (hour) return hour;
    }
    if (date) {
        const day = data.daily?.find(row => row.time === date);
        if (day) return day;
    }
    return data.current || null;
}

export function sceneWeather(data, selected, date, time) {
    if (!selected) return null;
    const isObserved = selected === data.current
        || Boolean(
            time
            && selected.time?.slice(0, 13) === data.current?.time?.slice(0, 13)
            && selected.time === data.current?.time,
        );
    const provenance = isObserved ? "observed" : "forecast";
    const daily = data.daily?.find(row => row.time === date);
    const solar = solarState(time || selected.time, daily, data.current);
    const weatherCode = selected.weather?.code ?? null;
    const cloudCover = selected.cloud_cover_percent ?? null;
    const precipitation = selected.precipitation_mm
        ?? selected.precipitation_sum_mm
        ?? null;
    const rain = selected.rain_mm ?? null;
    const windSpeed = selected.wind_speed_kmh ?? selected.wind_speed_max_kmh ?? null;
    const windDirection = selected.wind_direction_degrees ?? null;
    const temperature = selected.temperature_c ?? selected.temperature_max_c ?? null;
    const humidity = selected.relative_humidity_percent ?? null;
    const values = [
        weatherCode,
        cloudCover,
        precipitation,
        rain,
        windSpeed,
        windDirection,
        temperature,
        humidity,
    ];

    return {
        active: values.some(value => value !== null && value !== undefined),
        provenance,
        category: selected.weather?.category || "unknown",
        weatherCode,
        cloudCover,
        precipitation,
        rain,
        windSpeed,
        windDirectionDegrees: windDirection,
        temperatureC: temperature,
        humidityPercent: humidity,
        isNight: solar.isNight,
        daylightFactor: solar.daylightFactor,
        twilightFactor: solar.twilightFactor,
        solarProgress: solar.solarProgress,
        availability: {
            weather: fieldAvailability(weatherCode, provenance),
            cloudCover: fieldAvailability(cloudCover, provenance),
            precipitation: fieldAvailability(precipitation, provenance),
            rain: fieldAvailability(rain, provenance),
            windSpeed: fieldAvailability(windSpeed, provenance),
            windDirection: fieldAvailability(windDirection, provenance),
            temperature: fieldAvailability(temperature, provenance),
            humidity: fieldAvailability(humidity, provenance),
            daylight: fieldAvailability(solar.daylightFactor, solar.provenance),
        },
    };
}
