const numberFormat = new Intl.NumberFormat("fr-FR", {
    maximumFractionDigits: 1,
});

export function formatValue(value, unit = "") {
    if (value === null || value === undefined || !Number.isFinite(Number(value))) {
        return "—";
    }
    return `${numberFormat.format(Number(value))}${unit}`;
}

export function formatDate(dateString, options = {}) {
    if (!dateString) return "Date indisponible";
    const parts = dateString.split("-").map(Number);
    if (parts.length !== 3 || parts.some(Number.isNaN)) return dateString;
    const date = new Date(parts[0], parts[1] - 1, parts[2], 12);
    return new Intl.DateTimeFormat("fr-FR", {
        weekday: options.short ? undefined : "long",
        day: "numeric",
        month: options.short ? "short" : "long",
        ...(options.year ? { year: "numeric" } : {}),
    }).format(date);
}

export function formatHour(timeString) {
    if (typeof timeString !== "string") return "Heure indisponible";
    const match = timeString.match(/T(\d{2}:\d{2})/);
    return match ? match[1] : timeString;
}

export function formatRetrievedAt(value) {
    if (!value) return "Actualisation indisponible";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "Actualisation indisponible";
    return new Intl.DateTimeFormat("fr-FR", {
        dateStyle: "medium",
        timeStyle: "short",
    }).format(date);
}
