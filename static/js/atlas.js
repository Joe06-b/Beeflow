/* ==========================================================================
   ATLAS DES MALADIES
   - Inclinaison 3D des illustrations sous la souris (les couches se décalent en profondeur)
   - Cartes qui se retournent (recto : illustration, verso : fiche)
   - Filtres par catégorie et « seulement celles détectées chez moi »
   ========================================================================== */
(function () {
    "use strict";

    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const sfx = n => window.BeeFlow && BeeFlow.sfx.play(n);

    /* ---- Inclinaison 3D ---- */
    document.querySelectorAll("[data-tilt]").forEach(stage => {
        const illu = stage.querySelector(".illu");
        if (!illu || reduceMotion) return;
        let raf = 0;
        stage.addEventListener("pointermove", e => {
            const r = stage.getBoundingClientRect();
            const x = (e.clientX - r.left) / r.width - 0.5;      // -0.5 → 0.5
            const y = (e.clientY - r.top) / r.height - 0.5;
            cancelAnimationFrame(raf);
            raf = requestAnimationFrame(() => {
                stage.classList.add("is-tilting");
                illu.style.setProperty("--ry", (x * 34).toFixed(1) + "deg");
                illu.style.setProperty("--rx", (-y * 26).toFixed(1) + "deg");
            });
        });
        stage.addEventListener("pointerleave", () => {
            stage.classList.remove("is-tilting");
            illu.style.setProperty("--ry", "0deg");
            illu.style.setProperty("--rx", "0deg");
        });
    });

    // Petit mouvement automatique de l'illustration mise en avant, pour montrer qu'elle est en 3D
    const une = document.querySelector(".atlas-featured-stage .illu");
    if (une && !reduceMotion) {
        let t0 = performance.now(), actif = true;
        const stage = une.parentElement;
        stage.addEventListener("pointerenter", () => { actif = false; });
        stage.addEventListener("pointerleave", () => { actif = true; t0 = performance.now(); });
        (function balancer(now) {
            if (actif) {
                const t = (now - t0) / 1000;
                une.style.setProperty("--ry", (Math.sin(t * 0.8) * 16).toFixed(1) + "deg");
                une.style.setProperty("--rx", (Math.cos(t * 0.6) * 6).toFixed(1) + "deg");
            }
            requestAnimationFrame(balancer);
        })(t0);
    }

    /* ---- Retourner les cartes ---- */
    function flip(card, etat) {
        const flipped = etat === undefined ? !card.classList.contains("is-flipped") : etat;
        card.classList.toggle("is-flipped", flipped);
        card.querySelector(".atlas-front").setAttribute("aria-hidden", flipped);
        card.querySelector(".atlas-back").setAttribute("aria-hidden", !flipped);
        sfx("turn");
        // le focus suit la face visible
        const cible = card.querySelector(flipped ? ".atlas-back [data-flip]" : ".atlas-front [data-flip]");
        if (cible) setTimeout(() => cible.focus({ preventScroll: true }), 350);
    }
    document.querySelectorAll(".atlas-card [data-flip]").forEach(btn =>
        btn.addEventListener("click", () => flip(btn.closest(".atlas-card"))));

    // « Lire la fiche » depuis la mise en avant
    document.querySelectorAll("[data-open-card]").forEach(btn => btn.addEventListener("click", () => {
        const card = document.getElementById(btn.dataset.openCard);
        if (!card) return;
        card.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth", block: "center" });
        setTimeout(() => flip(card, true), reduceMotion ? 0 : 450);
    }));

    // Arrivée avec #slug dans l'adresse (depuis la fiche d'un suivi) : carte retournée
    if (location.hash) {
        const card = document.getElementById(decodeURIComponent(location.hash.slice(1)));
        if (card && card.classList.contains("atlas-card")) setTimeout(() => { card.scrollIntoView({ block: "center" }); flip(card, true); }, 500);
    }

    /* ---- Filtres ---- */
    const grid = document.getElementById("atlasGrid");
    if (!grid) return;
    const chips = document.querySelectorAll(".atlas-filters [data-filter]");
    const onlyDetected = document.getElementById("onlyDetected");
    const empty = document.getElementById("atlasEmpty");
    let filtre = "all";

    function appliquer() {
        let visibles = 0;
        grid.querySelectorAll(".atlas-card").forEach(card => {
            const ok = (filtre === "all" || card.dataset.cat === filtre) &&
                       (!onlyDetected.checked || Number(card.dataset.detected) > 0);
            card.hidden = !ok;
            if (ok) visibles++;
        });
        empty.hidden = visibles > 0;
    }
    chips.forEach(chip => chip.addEventListener("click", () => {
        chips.forEach(c => c.classList.toggle("is-active", c === chip));
        filtre = chip.dataset.filter;
        sfx("select");
        appliquer();
    }));
    onlyDetected.addEventListener("change", () => { sfx("select"); appliquer(); });
})();
