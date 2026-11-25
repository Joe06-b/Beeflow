/* ==========================================================================
   BEEFLOW — JavaScript commun (front office + back office)
     1. Fond dynamique en alvéoles (réagit au curseur)
     2. Toasts (messages Django + BeeFlow.toast() pour les autres scripts)
     3. Interface : date, compteurs, barres, menus mobiles, modules "bientôt"
   ========================================================================== */
(function () {
    "use strict";

    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const ICONS = document.body.dataset.icons || "/static/img/icons.svg";

    function icon(name, cls) {
        return `<svg class="ico ${cls || ""}" aria-hidden="true"><use href="${ICONS}#${name}"></use></svg>`;
    }

    /* ----------------------------------------------------------------------
       1. FOND EN ALVÉOLES
       Grille hexagonale très discrète ; les cellules proches du curseur
       se remplissent de miel, et quelques cellules "respirent" au hasard.
       ---------------------------------------------------------------------- */
    function honeycomb() {
        if (document.body.dataset.honeycomb === "off") return;

        const canvas = document.createElement("canvas");
        canvas.id = "bf-honeycomb";
        canvas.setAttribute("aria-hidden", "true");
        document.body.prepend(canvas);
        const ctx = canvas.getContext("2d");

        const strong = document.body.dataset.honeycomb === "strong";
        const R = 26;                         // rayon d'une alvéole (px)
        const W = Math.sqrt(3) * R;           // largeur
        const H = 1.5 * R;                    // pas vertical
        const RAYON_SOURIS = 150;
        const LINE = strong ? "rgba(233, 185, 73, 0.10)" : "rgba(133, 92, 11, 0.075)";
        let cells = [], grid = null, dpr = 1, w = 0, h = 0;
        const mouse = { x: -9999, y: -9999, active: false };

        function hexPath(c, x, y, r) {
            c.beginPath();
            for (let i = 0; i < 6; i++) {
                const a = Math.PI / 180 * (60 * i - 90);
                const px = x + r * Math.cos(a), py = y + r * Math.sin(a);
                i ? c.lineTo(px, py) : c.moveTo(px, py);
            }
            c.closePath();
        }

        function build() {
            dpr = Math.min(window.devicePixelRatio || 1, 2);
            w = window.innerWidth; h = window.innerHeight;
            canvas.width = w * dpr; canvas.height = h * dpr;
            ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

            cells = [];
            for (let row = -1, y = 0; y < h + R * 2; row++, y = row * H) {
                const offset = (row & 1) ? W / 2 : 0;
                for (let x = -W + offset; x < w + W; x += W) cells.push({ x, y, e: 0, pulse: 0 });
            }

            // La grille fixe est dessinée une seule fois dans un canvas hors écran
            grid = document.createElement("canvas");
            grid.width = canvas.width; grid.height = canvas.height;
            const g = grid.getContext("2d");
            g.setTransform(dpr, 0, 0, dpr, 0, 0);
            g.strokeStyle = LINE; g.lineWidth = 1;
            cells.forEach(c => { hexPath(g, c.x, c.y, R - 2); g.stroke(); });
        }

        function frame() {
            ctx.clearRect(0, 0, w, h);
            ctx.drawImage(grid, 0, 0, w, h);

            for (const c of cells) {
                let target = c.pulse;
                if (mouse.active) {
                    const d = Math.hypot(c.x - mouse.x, c.y - mouse.y);
                    if (d < RAYON_SOURIS) target = Math.max(target, 1 - d / RAYON_SOURIS);
                }
                c.e += (target - c.e) * 0.12;
                c.pulse *= 0.985;
                if (c.e > 0.015) {
                    hexPath(ctx, c.x, c.y, R - 2);
                    ctx.fillStyle = `rgba(233, 185, 73, ${(strong ? 0.30 : 0.22) * c.e})`;
                    ctx.fill();
                    ctx.strokeStyle = `rgba(201, 146, 26, ${0.45 * c.e})`;
                    ctx.stroke();
                }
            }
            if (document.hidden) running = false;
            else requestAnimationFrame(frame);
        }
        let running = false;
        function start() { if (!running) { running = true; requestAnimationFrame(frame); } }

        build();
        if (reduceMotion) { ctx.drawImage(grid, 0, 0, w, h); return; }

        window.addEventListener("resize", () => { build(); });
        window.addEventListener("pointermove", e => { mouse.x = e.clientX; mouse.y = e.clientY; mouse.active = true; }, { passive: true });
        document.addEventListener("pointerleave", () => { mouse.active = false; });
        document.addEventListener("visibilitychange", () => { if (!document.hidden) start(); });

        // Quelques alvéoles qui "respirent"
        setInterval(() => {
            if (!cells.length) return;
            cells[Math.floor(Math.random() * cells.length)].pulse = 0.55 + Math.random() * 0.35;
        }, 900);

        start();
    }

    /* ----------------------------------------------------------------------
       2. TOASTS
       ---------------------------------------------------------------------- */
    const TOAST_ICONS = { success: "check", error: "alert", warning: "alert", info: "bell" };

    function toastContainer() {
        let box = document.querySelector(".toasts");
        if (!box) {
            box = document.createElement("div");
            box.className = "toasts";
            box.setAttribute("aria-live", "polite");
            document.body.appendChild(box);
        }
        return box;
    }

    function dismiss(t) {
        if (!t || t.classList.contains("is-leaving")) return;
        t.classList.add("is-leaving");
        setTimeout(() => t.remove(), 260);
    }

    function armToast(t, delay) {
        const close = t.querySelector(".toast-close");
        if (close) close.addEventListener("click", () => dismiss(t));
        if (delay) setTimeout(() => dismiss(t), delay);
    }

    function toast(message, type) {
        type = type || "info";
        const t = document.createElement("div");
        t.className = `toast is-${type}`;
        t.setAttribute("role", type === "error" ? "alert" : "status");
        t.innerHTML = `<span class="hex">${icon(TOAST_ICONS[type] || "bell")}</span>
            <div class="toast-body">${message}</div>
            <button type="button" class="toast-close" aria-label="Fermer">${icon("x", "ico-sm")}</button>`;
        toastContainer().appendChild(t);
        armToast(t, 5000);
        return t;
    }

    window.BeeFlow = { toast, icon };

    /* ----------------------------------------------------------------------
       3. INTERFACE
       ---------------------------------------------------------------------- */
    document.addEventListener("DOMContentLoaded", () => {
        honeycomb();

        // Messages Django déjà présents dans la page
        document.querySelectorAll(".toasts .toast").forEach(t => armToast(t, 6000));

        // Date (back office)
        const dateElement = document.getElementById("currentDate");
        if (dateElement) {
            dateElement.textContent = new Date().toLocaleDateString("fr-FR", {
                weekday: "long", day: "numeric", month: "long", year: "numeric"
            });
        }

        // Compteurs animés
        document.querySelectorAll(".counter").forEach(counter => {
            const target = Number(counter.dataset.target) || 0;
            if (reduceMotion) { counter.textContent = target; return; }
            const start = performance.now(), duree = 900;
            const step = now => {
                const p = Math.min(1, (now - start) / duree);
                counter.textContent = Math.round(target * (1 - Math.pow(1 - p, 3)));
                if (p < 1) requestAnimationFrame(step);
            };
            requestAnimationFrame(step);
        });

        // Barres du graphique du tableau de bord
        document.querySelectorAll(".bar").forEach((bar, index) => {
            setTimeout(() => { bar.style.height = bar.dataset.height; }, reduceMotion ? 0 : index * 100);
        });

        // Menu mobile du back office
        const sidebar = document.getElementById("sidebar");
        document.querySelectorAll("[data-toggle-menu]").forEach(btn => {
            btn.addEventListener("click", () => sidebar && sidebar.classList.toggle("open"));
        });

        // Menu mobile du front office
        const frontNav = document.querySelector(".front-nav");
        document.querySelectorAll("[data-toggle-front]").forEach(btn => {
            btn.addEventListener("click", () => {
                const open = frontNav.classList.toggle("open");
                btn.setAttribute("aria-expanded", open);
            });
        });

        // Menu déroulant du compte (back office)
        document.querySelectorAll("[data-dropdown]").forEach(dd => {
            const btn = dd.querySelector("[data-dropdown-toggle]");
            const menu = dd.querySelector("[role=menu]");
            const setOpen = open => { menu.hidden = !open; btn.setAttribute("aria-expanded", open); };
            btn.addEventListener("click", e => { e.stopPropagation(); setOpen(menu.hidden); });
            document.addEventListener("click", e => { if (!dd.contains(e.target)) setOpen(false); });
            document.addEventListener("keydown", e => { if (e.key === "Escape") setOpen(false); });
            menu.addEventListener("click", e => { if (e.target.closest("button")) setOpen(false); });
        });

        // Fenêtres modales (<dialog>) : data-modal-open="id" / data-modal-close
        document.querySelectorAll("[data-modal-open]").forEach(btn => {
            btn.addEventListener("click", () => {
                const dlg = document.getElementById(btn.dataset.modalOpen);
                if (dlg && dlg.showModal) dlg.showModal();
            });
        });
        document.querySelectorAll("dialog.modal").forEach(dlg => {
            dlg.querySelectorAll("[data-modal-close]").forEach(b => b.addEventListener("click", () => dlg.close()));
            dlg.addEventListener("click", e => { if (e.target === dlg) dlg.close(); });   // clic sur le fond
        });

        // Formulaire « Modifier mon compte » : vérifications avant envoi
        document.querySelectorAll("[data-account-form]").forEach(form => {
            const erreur = form.querySelector("[data-form-error]");
            form.addEventListener("submit", e => {
                const v = name => (form.elements[name] ? form.elements[name].value.trim() : "");
                let msg = "";
                if (!v("username")) msg = "Le nom d'utilisateur est obligatoire.";
                else if (v("email") && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(v("email"))) msg = "L'adresse e-mail n'est pas valide.";
                else if (!v("old_password")) msg = "Saisissez votre mot de passe actuel pour enregistrer.";
                else if (v("new_password1") && v("new_password1").length < 8) msg = "Le nouveau mot de passe doit contenir au moins 8 caractères.";
                else if (v("new_password1") !== v("new_password2")) msg = "Les deux nouveaux mots de passe ne sont pas identiques.";
                erreur.hidden = !msg;
                erreur.innerHTML = msg ? icon("alert") + " " + msg : "";
                if (msg) { e.preventDefault(); return; }
                if (form.hasAttribute("data-demo")) {          // pas encore branché au module utilisateurs
                    e.preventDefault();
                    form.closest("dialog").close();
                    toast("Formulaire valide. L'enregistrement sera actif après l'intégration du module <strong>Gestion des utilisateurs</strong>.", "info");
                }
            });
        });

        // Formulaire « Supprimer mon compte » : bouton actif seulement avec le mot de passe
        document.querySelectorAll("[data-delete-account-form]").forEach(form => {
            const mdp = form.querySelector("input[type=password]");
            const btn = form.querySelector("button[type=submit]");
            mdp.addEventListener("input", () => { btn.disabled = !mdp.value; });
            form.addEventListener("submit", e => {
                if (!mdp.value) { e.preventDefault(); return; }
                if (form.hasAttribute("data-demo")) {
                    e.preventDefault();
                    form.closest("dialog").close();
                    toast("La suppression du compte sera active après l'intégration du module <strong>Gestion des utilisateurs</strong>.", "warning");
                }
            });
        });

        // Modules pas encore développés (attribut data-soon)
        document.querySelectorAll("[data-soon]").forEach(link => {
            link.addEventListener("click", event => {
                event.preventDefault();
                const title = link.dataset.title || link.textContent.replace(/bientôt/i, "").trim();
                toast(`Le module <strong>${title}</strong> sera disponible après l'intégration de l'équipe.`, "info");
                if (sidebar && window.innerWidth <= 860) sidebar.classList.remove("open");
            });
        });
    });
})();
