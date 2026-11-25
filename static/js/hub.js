/* ==========================================================================
   PAGE « MON ESPACE » — rotation de la ruche 3D
   - Glisser (souris / doigt) pour tourner, avec aimantation sur la face la plus proche
   - Flèches du clavier ← → pour tourner, Entrée pour ouvrir la face de devant
   - Clic sur une face de côté : elle vient devant ; clic sur la face de devant : ouverture
   - Rotation automatique douce tant que l'utilisateur n'a pas touché la ruche
   ========================================================================== */
(function () {
    "use strict";

    const stage = document.getElementById("hiveStage");
    const hive = document.getElementById("hive");
    if (!stage || !hive) return;

    const faces = Array.from(hive.querySelectorAll(".face"));
    const listButtons = Array.from(document.querySelectorAll(".espace-list [data-face]"));
    const N = faces.length;                 // 6 faces
    const STEP = 360 / N;                   // 60°
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    let angle = 0;                          // rotation actuelle (degrés)
    let autoTimer = null;

    const frontIndex = () => ((Math.round(-angle / STEP) % N) + N) % N;

    function render() {
        hive.style.setProperty("--angle", angle + "deg");
        const front = frontIndex();
        faces.forEach((f, i) => {
            const isFront = i === front;
            f.classList.toggle("is-front", isFront);
            f.tabIndex = -1;                                   // la scène gère le clavier
            f.setAttribute("aria-hidden", isFront ? "false" : "true");
        });
        listButtons.forEach(b => {
            const cur = Number(b.dataset.face) === front;
            b.classList.toggle("is-current", cur);
            b.setAttribute("aria-current", cur ? "true" : "false");
        });
    }

    function goTo(index) {
        // chemin le plus court vers la face demandée
        const target = -index * STEP;
        let diff = ((target - angle) % 360 + 540) % 360 - 180;
        angle += diff;
        render();
    }
    const turn = dir => { angle -= dir * STEP; angle = Math.round(angle / STEP) * STEP; render(); };

    function open(face) {
        if (face.hasAttribute("data-locked")) {
            window.BeeFlow && BeeFlow.toast("L'<strong>administration</strong> est réservée au compte administrateur.", "warning");
            return;
        }
        if (face.hasAttribute("data-soon")) {
            face.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true }));   // toast "bientôt" (beeflow.js)
            return;
        }
        if (reduceMotion) { window.location.href = face.href; return; }
        stage.classList.add("is-opening");
        setTimeout(() => { window.location.href = face.href; }, 520);
    }

    function stopAuto() { clearInterval(autoTimer); autoTimer = null; }

    /* ---- Glisser ---- */
    // Empêche le glisser-déposer natif des liens/images, qui bloquerait la rotation
    hive.querySelectorAll("a, img").forEach(el => el.setAttribute("draggable", "false"));
    stage.addEventListener("dragstart", e => e.preventDefault());

    let dragging = false, moved = false, startX = 0, startAngle = 0, lastX = 0, lastT = 0, velocity = 0;

    stage.addEventListener("pointerdown", e => {
        if (e.button !== 0) return;
        stopAuto();
        dragging = true; moved = false;
        startX = lastX = e.clientX; startAngle = angle; lastT = performance.now(); velocity = 0;
    });
    window.addEventListener("pointermove", e => {
        if (!dragging) return;
        const dx = e.clientX - startX;
        if (!moved && Math.abs(dx) > 6) {
            moved = true;
            stage.classList.add("is-dragging");
            stage.setPointerCapture && stage.setPointerCapture(e.pointerId);
        }
        if (!moved) return;
        const now = performance.now();
        velocity = (e.clientX - lastX) / Math.max(1, now - lastT);
        lastX = e.clientX; lastT = now;
        angle = startAngle + dx * 0.35;
        hive.style.setProperty("--angle", angle + "deg");
    });
    window.addEventListener("pointerup", () => {
        if (!dragging) return;
        dragging = false;
        stage.classList.remove("is-dragging");
        if (moved) {
            angle += velocity * 60;                       // élan
            angle = Math.round(angle / STEP) * STEP;       // aimantation
            render();
        }
    });

    /* ---- Clic sur une face ---- */
    faces.forEach((face, i) => {
        face.addEventListener("click", e => {
            if (moved) { e.preventDefault(); e.stopImmediatePropagation(); return; }
            if (i !== frontIndex()) {                      // face de côté : on la ramène devant
                e.preventDefault(); e.stopImmediatePropagation();
                stopAuto(); goTo(i);
                return;
            }
            if (face.hasAttribute("data-locked")) { e.preventDefault(); open(face); return; }
            if (!face.hasAttribute("data-soon")) { e.preventDefault(); open(face); }
            // data-soon : beeflow.js affiche le toast "bientôt disponible"
        }, true);
    });

    /* ---- Liste des modules ---- */
    listButtons.forEach(b => b.addEventListener("click", () => {
        stopAuto();
        const i = Number(b.dataset.face);
        if (i === frontIndex()) open(faces[i]); else goTo(i);
    }));

    /* ---- Boutons et clavier ---- */
    document.querySelectorAll("[data-turn]").forEach(b =>
        b.addEventListener("click", () => { stopAuto(); turn(Number(b.dataset.turn)); }));

    stage.addEventListener("keydown", e => {
        if (e.key === "ArrowRight") { e.preventDefault(); stopAuto(); turn(1); }
        else if (e.key === "ArrowLeft") { e.preventDefault(); stopAuto(); turn(-1); }
        else if (e.key === "Enter" || e.key === " ") { e.preventDefault(); open(faces[frontIndex()]); }
    });

    /* ---- Démarrage ---- */
    render();
    if (!reduceMotion) {
        hive.classList.add("is-intro");
        setTimeout(() => hive.classList.remove("is-intro"), 1400);
        autoTimer = setInterval(() => turn(1), 3800);
        stage.addEventListener("pointerenter", stopAuto, { once: true });
    }
})();
