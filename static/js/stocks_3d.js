/* ==========================================================================
   MODULE GESTION DU STOCK — vue 3D « alvéoles » (front office)
   1. Bascule Vue 3D / Vue tableau sur la liste (choix mémorisé dans le navigateur)
   2. Fiche détail : la grande alvéole tourne au glisser (souris / doigt) et au clavier
   ========================================================================== */
(function () {
    "use strict";

    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    /* ---- 1. Bascule des vues ---- */
    const boutons = Array.from(document.querySelectorAll("[data-st-vue]"));
    if (boutons.length) {
        const CLE = "beeflow.stocks.vue";
        const vues = Array.from(document.querySelectorAll(".st-vue"));

        function afficher(nom) {
            vues.forEach(v => { v.hidden = v.dataset.vue !== nom; });
            boutons.forEach(b => b.setAttribute("aria-pressed", b.dataset.stVue === nom ? "true" : "false"));
            try { localStorage.setItem(CLE, nom); } catch (e) { /* stockage indisponible : on ignore */ }
        }

        let depart = "3d";
        try { depart = localStorage.getItem(CLE) || "3d"; } catch (e) { /* idem */ }
        afficher(depart === "tableau" ? "tableau" : "3d");
        boutons.forEach(b => b.addEventListener("click", () => afficher(b.dataset.stVue)));
    }

    /* ---- 2. Rotation de la grande alvéole ---- */
    const scene = document.querySelector(".st-cell-xl");
    if (!scene) return;
    const prisme = scene.querySelector(".st-prism");
    let angle = 30;
    let glisse = false, x0 = 0, angle0 = 0, auto = null;

    const appliquer = () => prisme.style.setProperty("--ry", angle + "deg");
    const stopAuto = () => { if (auto) { cancelAnimationFrame(auto); auto = null; } };

    scene.addEventListener("pointerdown", e => {
        if (e.button !== 0) return;
        stopAuto();
        glisse = true; x0 = e.clientX; angle0 = angle;
        scene.classList.add("is-dragging");
        scene.setPointerCapture && scene.setPointerCapture(e.pointerId);
    });
    scene.addEventListener("pointermove", e => {
        if (!glisse) return;
        angle = angle0 + (e.clientX - x0) * .5;
        appliquer();
    });
    const fin = () => { glisse = false; scene.classList.remove("is-dragging"); };
    scene.addEventListener("pointerup", fin);
    scene.addEventListener("pointercancel", fin);

    scene.addEventListener("keydown", e => {
        if (e.key === "ArrowRight") { e.preventDefault(); stopAuto(); angle += 30; appliquer(); }
        else if (e.key === "ArrowLeft") { e.preventDefault(); stopAuto(); angle -= 30; appliquer(); }
    });

    // Rotation lente au chargement, jusqu'à ce que l'utilisateur prenne la main
    if (!reduceMotion) {
        prisme.style.transition = "none";
        const tourner = () => { angle += .25; appliquer(); auto = requestAnimationFrame(tourner); };
        auto = requestAnimationFrame(tourner);
        scene.addEventListener("pointerenter", () => { stopAuto(); prisme.style.transition = ""; }, { once: true });
        scene.addEventListener("focus", () => { stopAuto(); prisme.style.transition = ""; }, { once: true });
    } else {
        appliquer();
    }
})();