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

    /* ----------------------------------------------------------------------
       EFFETS SONORES (Web Audio API, aucun fichier)
       Préférence partagée avec l'intro : localStorage "beeflow_son" ("0" = coupé)
       ---------------------------------------------------------------------- */
    const sfx = (function () {
        let A = null;
        const on = () => { try { return localStorage.getItem("beeflow_son") !== "0"; } catch (e) { return true; } };
        function ctxA() {
            if (!A) { try { A = new (window.AudioContext || window.webkitAudioContext)(); } catch (e) { return null; } }
            if (A.state === "suspended") A.resume().catch(() => {});
            return A;
        }
        function tone(freq, type, start, dur, vol, freqEnd) {
            const o = A.createOscillator(), g = A.createGain(), t = A.currentTime + start;
            o.type = type; o.frequency.setValueAtTime(freq, t);
            if (freqEnd) o.frequency.exponentialRampToValueAtTime(freqEnd, t + dur);
            g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(vol, t + 0.008);
            g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
            o.connect(g).connect(A.destination); o.start(t); o.stop(t + dur + 0.05);
        }
        function noise(start, dur, f1, f2, vol) {
            const t = A.currentTime + start;
            const b = A.createBuffer(1, Math.floor(A.sampleRate * dur), A.sampleRate), d = b.getChannelData(0);
            for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
            const src = A.createBufferSource(); src.buffer = b;
            const f = A.createBiquadFilter(); f.type = "bandpass"; f.Q.value = 0.9;
            f.frequency.setValueAtTime(f1, t); f.frequency.exponentialRampToValueAtTime(f2, t + dur);
            const g = A.createGain(); g.gain.setValueAtTime(0.0001, t);
            g.gain.exponentialRampToValueAtTime(vol, t + dur * 0.3); g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
            src.connect(f).connect(g).connect(A.destination); src.start(t);
        }
        const SONS = {
            turn()   { noise(0, 0.28, 500, 1300, 0.05); tone(340, "triangle", 0, 0.07, 0.06); },   // rotation de la ruche
            select() { tone(660, "sine", 0, 0.09, 0.05); },                                         // choix dans la liste
            open()   { noise(0, 0.75, 280, 2600, 0.12); tone(783.99, "sine", 0.18, 0.9, 0.08); tone(1046.5, "sine", 0.32, 1.1, 0.08); },
            enter()  { noise(0, 0.6, 2200, 400, 0.07); tone(1046.5, "sine", 0.05, 0.8, 0.05); }, // arrivée sur un module
            locked() { tone(150, "triangle", 0, 0.16, 0.16, 95); tone(150, "triangle", 0.15, 0.2, 0.14, 85); },
            soon()   { tone(880, "sine", 0, 0.12, 0.06); tone(660, "sine", 0.11, 0.18, 0.06); },
            // CRUD
            ajout()        { tone(523.25, "sine", 0, 0.35, 0.09); tone(659.25, "sine", 0.1, 0.35, 0.09); tone(783.99, "sine", 0.2, 0.6, 0.1); },
            modification() { tone(659.25, "sine", 0, 0.25, 0.08); tone(880, "sine", 0.12, 0.5, 0.08); noise(0, 0.12, 2500, 3500, 0.03); },
            suppression()  { noise(0, 0.45, 2200, 300, 0.12); tone(392, "triangle", 0.05, 0.25, 0.07, 260); tone(260, "triangle", 0.22, 0.3, 0.06, 180); },
            erreur()       { tone(220, "square", 0, 0.12, 0.035); tone(196, "square", 0.14, 0.2, 0.035); },
            // Règles du formulaire
            regleOk() { tone(1046.5, "sine", 0, 0.18, 0.05); tone(1318.5, "sine", 0.06, 0.25, 0.04); },
            regleKo() { tone(330, "triangle", 0, 0.16, 0.06, 250); },
        };
        return {
            play(name) { if (!on() || !SONS[name] || !ctxA()) return; try { SONS[name](); } catch (e) {} },
            enabled: on,
            set(v) { try { localStorage.setItem("beeflow_son", v ? "1" : "0"); } catch (e) {} },
        };
    })();

    window.BeeFlow = { toast, icon, sfx };

    /* ----------------------------------------------------------------------
       3. INTERFACE
       ---------------------------------------------------------------------- */
    document.addEventListener("DOMContentLoaded", () => {
        honeycomb();

        // Messages Django déjà présents dans la page (+ son associé : data-son="son-ajout"...)
        document.querySelectorAll(".toasts .toast").forEach(t => armToast(t, 6000));
        const sonMessage = document.querySelector(".toasts .toast[data-son]");
        if (sonMessage) sfx.play(sonMessage.dataset.son.replace("son-", ""));

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

        // Boutons « son activé / coupé » (data-sound-toggle)
        document.querySelectorAll("[data-sound-toggle]").forEach(btn => {
            const draw = () => {
                const v = sfx.enabled();
                btn.innerHTML = icon(v ? "volume" : "volume-off");
                btn.title = v ? "Couper le son" : "Activer le son";
                btn.setAttribute("aria-label", btn.title);
                btn.setAttribute("aria-pressed", v);
            };
            draw();
            btn.addEventListener("click", () => { sfx.set(!sfx.enabled()); draw(); sfx.play("select"); });
        });

        // Arrivée depuis la ruche 3D : l'écran miel s'ouvre par une alvéole qui s'agrandit
        const enter = document.getElementById("pageEnter");
        if (enter) {
            sfx.play("enter");
            const W = window.innerWidth, H = window.innerHeight, cx = W / 2, cy = H / 2;
            const maxR = Math.hypot(W, H) * 0.62, duree = reduceMotion ? 1 : 750, t0 = performance.now();
            const hex = r => Array.from({ length: 6 }, (_, i) => {
                const a = Math.PI / 180 * (60 * i - 90);
                return `${(cx + r * Math.cos(a)).toFixed(1)}px ${(cy + r * Math.sin(a)).toFixed(1)}px`;
            }).join(", ");
            enter.classList.add("is-leaving");
            const step = now => {
                const k = Math.min(1, (now - t0 - 180) / duree);
                if (k > 0) {
                    const e = k * k * (3 - 2 * k);
                    const r = 8 + e * maxR;
                    enter.style.clipPath = `polygon(evenodd, 0 0, ${W}px 0, ${W}px ${H}px, 0 ${H}px, 0 0, ${hex(r)}, ${hex(r).split(", ")[0]})`;
                }
                if (k < 1) requestAnimationFrame(step); else enter.remove();
            };
            requestAnimationFrame(step);
        }

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
                else if (!v("telephone")) msg = "Le numéro de téléphone est obligatoire.";
                else if (!/^\+?[0-9]{8,12}$/.test(v("telephone").replace(/\s+/g, ''))) msg = "Numéro de téléphone invalide (8 à 12 chiffres).";
                else if (!v("date_naissance")) msg = "La date de naissance est obligatoire.";
                else if (!v("sexe")) msg = "Veuillez sélectionner le sexe.";
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
                sfx.play("soon");
                const title = link.dataset.title || link.textContent.replace(/bientôt/i, "").trim();
                toast(`Le module <strong>${title}</strong> sera disponible après l'intégration de l'équipe.`, "info");
                if (sidebar && window.innerWidth <= 860) sidebar.classList.remove("open");
            });
        });
    });
})();
