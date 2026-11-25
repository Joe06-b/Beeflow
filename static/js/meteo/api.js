export class MeteoApiError extends Error {
    constructor(message, status = 0, code = "network_error") {
        super(message);
        this.name = "MeteoApiError";
        this.status = status;
        this.code = code;
    }
}

export async function fetchJson(url, options = {}) {
    let response;
    try {
        response = await fetch(url, {
            ...options,
            credentials: "same-origin",
            headers: { Accept: "application/json", ...options.headers },
        });
    } catch (error) {
        if (error.name === "AbortError") throw error;
        throw new MeteoApiError(
            "Le serveur météo est inaccessible. Vérifiez votre connexion puis réessayez.",
            0,
            "network_error",
        );
    }

    let payload;
    try {
        payload = await response.json();
    } catch (error) {
        if (error.name === "AbortError") throw error;
        throw new MeteoApiError(
            "La réponse du serveur météo est illisible.",
            response.status,
            "invalid_response",
        );
    }

    if (!response.ok) {
        const detail = payload.error || {};
        throw new MeteoApiError(
            detail.message || "Les données météo n'ont pas pu être chargées.",
            response.status,
            detail.code || payload.status || "request_failed",
        );
    }
    return payload;
}

export function withZoneId(urlTemplate, zoneId) {
    return urlTemplate.replace("__ZONE_ID__", encodeURIComponent(zoneId));
}

export function csrfToken(form) {
    return form.querySelector("[name=csrfmiddlewaretoken]")?.value || "";
}
