/* ==========================================================================
   ÉVOLUTION D'UNE MALADIE DANS LA RUCHE — simulation + frise + chiffres + courbe
   Script classique (pas un module) : tout fonctionne même si la 3D ne démarre pas.
   La scène 3D (evolution3d.js) écoute l'évènement « evo:etat » pour se mettre à jour.

   Simulation (pédagogique), semaine par semaine :
     atteinte  I(t+1) = I + vitesse × I × (1 − I)          propagation en « S »
     abeilles  P(t+1) = P × (1 + croissance − dégâts × I)  la maladie tue, la saison fait naître
     traitement : à la semaine T, I est réduit de « efficacité », puis repart 4 fois moins vite
   ========================================================================== */
(function () {
    "use strict";

    const D = JSON.parse(document.getElementById("evoData").textContent);
    const S = D.semaines, P0 = D.population, T = D.traitement.semaine;
    const TRANSVASEMENT = D.slug === "loque-americaine";      // les cadres sont remplacés : couvain repart de zéro
    const CROISSANCE = 0.012;                     // naissances de la saison, par semaine
    const icon = (n, c) => (window.BeeFlow ? window.BeeFlow.icon(n, c) : "");
    const sfx = n => window.BeeFlow && window.BeeFlow.sfx.play(n);
    const fmt = n => Math.round(n).toLocaleString("fr-FR");

    /* ------------------------------------------------------------------ Simulation */
    function simuler(avec) {
        const pts = [];
        let I = D.depart, P = P0;
        for (let t = 0; t <= S; t++) {
            pts.push({ t, I, P });
            let r = D.vitesse;
            if (avec && t === T) I *= 1 - D.traitement.efficacite;
            if (avec && t >= T) r *= 0.25;
            I = Math.min(0.97, I + r * I * (1 - I));
            let croissance = CROISSANCE;
            if (avec && TRANSVASEMENT && t >= T && t < T + 3) croissance = -0.03;  // pas de naissances le temps que le couvain revienne
            P = Math.max(P0 * 0.04, P * (1 + croissance - D.degats * I));
        }
        return pts;
    }
    const SIM = { sans: simuler(false), avec: simuler(true) };

    /* ------------------------------------------------------------------ Étapes */
    function etapes(scenario) {
        if (scenario === "sans") return D.etapes;
        return D.etapes.filter(e => e.semaine < T).concat(D.apres_traitement);
    }
    function etapeCourante(scenario, t) {
        const liste = etapes(scenario);
        let cur = liste[0];
        liste.forEach(e => { if (e.semaine <= t) cur = e; });
        return cur;
    }

    function etatColonie(p) {
        if (p.I > 0.5 || p.P < P0 * 0.55) return { code: "critique", label: "Critique", cls: "is-bad" };
        if (p.I > 0.15 || p.P < P0 * 0.85) return { code: "moyen", label: "Moyen", cls: "is-warn" };
        return { code: "bon", label: "Bon", cls: "is-good" };
    }

    const LIBELLE_ATTEINTE = { couvain: "Couvain atteint", adultes: "Abeilles atteintes", butineuses: "Pression des frelons" };

    /* ------------------------------------------------------------------ État partagé */
    const etat = { semaine: 0, scenario: "sans" };
    window.EVO = { data: D, sim: SIM, etat, transvasement: TRANSVASEMENT };

    const $ = id => document.getElementById(id);
    const range = $("evoRange"), playBtn = $("evoPlay");

    // Repères sous la frise : étapes + semaine de traitement
    function dessinerRepères() {
        const box = $("evoMarks");
        box.innerHTML = "";
        for (let t = 0; t <= S; t++) {
            const m = document.createElement("span");
            m.style.left = (t / S * 100) + "%";
            const est = etapes(etat.scenario).some(e => e.semaine === t);
            if (etat.scenario === "avec" && t === T) { m.className = "is-treat"; m.title = "Traitement"; }
            else if (est) m.className = "is-step";
            box.appendChild(m);
        }
    }

    function dessinerEtapes() {
        const ol = $("evoSteps");
        ol.innerHTML = "";
        etapes(etat.scenario).forEach(e => {
            const li = document.createElement("li");
            const traite = etat.scenario === "avec" && e.semaine === T;
            li.innerHTML = `<button type="button" data-semaine="${e.semaine}"${traite ? ' class="is-treat"' : ""}>
                <span class="evo-step-week">S${e.semaine}</span><span>${e.titre}</span></button>`;
            ol.appendChild(li);
        });
    }

    function majUI(sonEtape) {
        const t = etat.semaine, p = SIM[etat.scenario][t], p0 = SIM[etat.scenario][0];
        range.value = t;
        range.style.setProperty("--pct", (t / S * 100) + "%");
        $("evoWeekBig").textContent = t;
        $("evoWeekLabel").textContent = `Semaine ${t} sur ${S}`;

        // Chiffres
        $("kpiPop").textContent = fmt(Math.round(p.P / 100) * 100);
        const delta = Math.round((p.P / p0.P - 1) * 100);
        $("kpiPopDelta").textContent = t === 0 ? "au départ" : `${delta > 0 ? "+" : ""}${delta} % depuis le départ`;
        $("kpiPopDelta").className = delta < -15 ? "is-bad" : delta < 0 ? "is-warn" : "is-good";
        $("kpiAtteinteLabel").textContent = LIBELLE_ATTEINTE[D.cible];
        const pct = Math.round(p.I * 100);
        $("kpiAtteinte").textContent = pct + " %";
        const bar = $("kpiAtteinteBar");
        bar.style.width = pct + "%";
        bar.className = pct > 50 ? "is-bad" : pct > 15 ? "is-warn" : "is-good";
        const e = etatColonie(p);
        const badge = $("kpiEtat");
        badge.textContent = e.label;
        badge.className = "badge " + e.cls;

        // Étape en cours
        const cur = etapeCourante(etat.scenario, t);
        const traite = etat.scenario === "avec" && t >= T;
        $("evoStep").innerHTML = `
            <p class="b3d-kicker">${icon(traite ? "flask" : "microbe", "ico-sm")} Semaine ${cur.semaine}${traite ? ", après traitement" : ""}</p>
            <h2>${cur.titre}</h2>
            <p>${cur.texte}</p>
            ${etat.scenario === "avec" && t >= T - 1 && t <= T ? `<div class="notice is-good">${icon("flask")}<div><strong>Action en semaine ${T}</strong>${D.traitement.action}</div></div>` : ""}
            ${etat.scenario === "sans" && t >= T - 1 && t <= T + 1 ? `<div class="notice is-warn">${icon("clock")}<div><strong>Moment idéal pour agir</strong>Passez en « Avec traitement » pour voir la différence.</div></div>` : ""}`;
        document.querySelectorAll("#evoSteps button").forEach(b => {
            const s = +b.dataset.semaine;
            b.classList.toggle("is-current", s === cur.semaine);
            b.classList.toggle("is-past", s < cur.semaine);
        });
        if (sonEtape && cur.semaine === t) sfx(traite && t === T ? "regleOk" : "soon");

        if (chart) chart.update("none");
        document.dispatchEvent(new CustomEvent("evo:etat", { detail: { semaine: t, scenario: etat.scenario, point: p } }));
    }

    function allerA(t, son) {
        t = Math.max(0, Math.min(S, t));
        if (t === etat.semaine) return;
        etat.semaine = t;
        majUI(son);
    }

    /* ------------------------------------------------------------------ Lecture automatique */
    let timer = null;
    function stop() {
        clearInterval(timer); timer = null;
        playBtn.setAttribute("aria-pressed", "false");
        playBtn.setAttribute("aria-label", "Lancer l'évolution");
    }
    function play() {
        if (etat.semaine >= S) allerA(0, false);
        playBtn.setAttribute("aria-pressed", "true");
        playBtn.setAttribute("aria-label", "Mettre en pause");
        sfx("select");
        timer = setInterval(() => {
            allerA(etat.semaine + 1, true);
            if (etat.semaine >= S) stop();
        }, 1300);
    }
    playBtn.addEventListener("click", () => (timer ? stop() : play()));
    range.addEventListener("input", () => { stop(); allerA(+range.value, true); });
    $("evoSteps").addEventListener("click", e => {
        const b = e.target.closest("button[data-semaine]");
        if (b) { stop(); allerA(+b.dataset.semaine, true); }
    });
    document.addEventListener("keydown", e => {
        if (e.target.closest("input, select, textarea")) return;
        if (e.key === "ArrowRight") { stop(); allerA(etat.semaine + 1, true); }
        if (e.key === "ArrowLeft") { stop(); allerA(etat.semaine - 1, true); }
    });

    document.querySelectorAll(".evo-switch button").forEach(b => b.addEventListener("click", () => {
        if (etat.scenario === b.dataset.scenario) return;
        etat.scenario = b.dataset.scenario;
        document.querySelectorAll(".evo-switch button").forEach(x => {
            const on = x === b;
            x.classList.toggle("is-active", on);
            x.setAttribute("aria-pressed", on);
        });
        sfx(etat.scenario === "avec" ? "regleOk" : "regleKo");
        dessinerRepères();
        dessinerEtapes();
        if (chart) {
            chart.data.datasets.forEach(ds => { ds.borderWidth = ds.scenario === etat.scenario ? 3 : 2; });
        }
        majUI(false);
    }));

    /* ------------------------------------------------------------------ Courbe */
    const BRUN = "#9C5A2E", MIEL = "#C98A00", GRILLE = "#EFE6D6", ENCRE = "#7A6A5B";
    let chart = null;
    if (window.Chart) {
        Chart.defaults.font.family = getComputedStyle(document.body).getPropertyValue("--font-body") || "Figtree, sans-serif";
        Chart.defaults.color = ENCRE;
        // Trait vertical : semaine affichée + repère du traitement
        const repere = {
            id: "repere",
            afterDatasetsDraw(c) {
                const { ctx, chartArea: a, scales: { x } } = c;
                ctx.save();
                const xt = x.getPixelForValue(T);
                ctx.strokeStyle = MIEL; ctx.setLineDash([3, 4]); ctx.lineWidth = 1.5;
                ctx.beginPath(); ctx.moveTo(xt, a.top); ctx.lineTo(xt, a.bottom); ctx.stroke();
                ctx.setLineDash([]); ctx.fillStyle = "#855C0B"; ctx.font = "600 12px " + Chart.defaults.font.family;
                ctx.textAlign = "left"; ctx.fillText("Traitement", xt + 6, a.top + 12);
                const xs = x.getPixelForValue(etat.semaine);
                ctx.strokeStyle = "#2B1B0F"; ctx.lineWidth = 2;
                ctx.beginPath(); ctx.moveTo(xs, a.top); ctx.lineTo(xs, a.bottom); ctx.stroke();
                ctx.restore();
            },
        };
        const serie = (sc, label, color, dash) => ({
            label, scenario: sc, data: SIM[sc].map(p => Math.round(p.P)),
            borderColor: color, backgroundColor: color, borderWidth: sc === etat.scenario ? 3 : 2, borderDash: dash,
            pointRadius: 0, pointHoverRadius: 5, tension: 0.35, cubicInterpolationMode: "monotone",
        });
        chart = new Chart($("evoChart"), {
            type: "line",
            data: {
                labels: SIM.sans.map(p => "S" + p.t),
                datasets: [serie("sans", "Sans traitement", BRUN, [6, 4]), serie("avec", "Avec traitement", MIEL, [])],
            },
            options: {
                maintainAspectRatio: false,
                animation: { duration: 600 },
                interaction: { mode: "index", intersect: false },
                onClick: (e, els, c) => {
                    const v = c.scales.x.getValueForPixel(e.x);
                    if (v != null) { stop(); allerA(Math.round(v), true); }
                },
                plugins: {
                    legend: { position: "top", align: "start", labels: { usePointStyle: true, pointStyle: "line", boxWidth: 26, padding: 16 } },
                    tooltip: { callbacks: { title: it => "Semaine " + it[0].dataIndex, label: c => ` ${c.dataset.label} : ${fmt(c.raw)} abeilles` } },
                },
                scales: {
                    x: { grid: { display: false }, border: { color: GRILLE } },
                    y: { beginAtZero: true, grid: { color: GRILLE }, border: { display: false }, ticks: { callback: v => fmt(v) } },
                },
            },
            plugins: [repere],
        });
    }

    dessinerRepères();
    dessinerEtapes();
    majUI(false);
})();
