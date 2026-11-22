/* ==========================================================================
   BeeFlow – Statistiques des produits (back office)
   KPI et graphiques : tout vient des données réelles.
   La page se rafraîchit toute seule (toutes les 15 s et au retour sur l'onglet).
   ========================================================================== */
(function () {
  "use strict";

  const brut = document.getElementById("pr-stats-data");
  if (!brut) return;
  const cfg = document.getElementById("pr-stats-config");
  const URL_DONNEES = cfg ? cfg.dataset.url : null;
  const ICONS = document.body.dataset.icons || "/static/img/icons.svg";
  const INTERVALLE_MS = 15000;
  const aDesGraphiques = !!document.getElementById("chart-etat");

  const COULEUR = { disponible: "#E9B949", rupture_stock: "#654321", archive: "#D9C7A3" };   // palette BeeFlow : miel / brun / cire
  const SERIE_1 = "#654321", SERIE_2 = "#E9B949", GRILLE = "#EFE6D6";

  /* ---------------- Graphiques ---------------- */
  const graphiques = {};
  function creerGraphiques(d) {
    if (typeof Chart === "undefined" || !aDesGraphiques) return;
    Chart.defaults.font.family = "Figtree, 'Segoe UI', sans-serif";
    Chart.defaults.font.size = 12.5;
    Chart.defaults.color = "#7A6A5B";
    Chart.defaults.plugins.tooltip.backgroundColor = "#2B1B0F";
    Chart.defaults.plugins.tooltip.titleColor = "#E9B949";
    Chart.defaults.plugins.tooltip.padding = 10;
    Chart.defaults.plugins.tooltip.cornerRadius = 10;
    const legende = { position: "top", align: "start", labels: { usePointStyle: true, pointStyle: "circle", boxWidth: 8, boxHeight: 8, padding: 16 } };

    graphiques.etat = new Chart(document.getElementById("chart-etat"), {
      type: "doughnut",
      data: { labels: d.par_etat.labels, datasets: [{ data: d.par_etat.data, backgroundColor: d.par_etat.keys.map(k => COULEUR[k]), borderColor: "#fff", borderWidth: 3 }] },
      options: { maintainAspectRatio: false, cutout: "62%", plugins: { legend: { ...legende, position: "right" }, tooltip: { callbacks: { label: c => ` ${c.raw} produit(s)` } } } },
    });

    graphiques.categorie = new Chart(document.getElementById("chart-categorie"), {
      type: "bar",
      data: { labels: d.par_categorie.labels, datasets: seriesCategorie(d) },
      options: {
        maintainAspectRatio: false,
        plugins: { legend: legende, tooltip: { callbacks: { label: c => ` ${c.dataset.label} : ${c.raw}` } } },
        scales: { x: { stacked: true, grid: { display: false }, border: { color: GRILLE } },
                  y: { stacked: true, beginAtZero: true, ticks: { precision: 0 }, grid: { color: GRILLE }, border: { display: false } } },
      },
    });

    graphiques.evolution = new Chart(document.getElementById("chart-evolution"), {
      data: { labels: d.evolution.labels, datasets: seriesEvolution(d) },
      options: {
        maintainAspectRatio: false, interaction: { mode: "index", intersect: false },
        plugins: { legend: legende },
        scales: {
          x: { grid: { display: false }, border: { color: GRILLE } },
          y: { beginAtZero: true, ticks: { precision: 0 }, grid: { color: GRILLE }, border: { display: false }, title: { display: true, text: "Ajoutés / mois" } },
          y1: { position: "right", beginAtZero: true, ticks: { precision: 0 }, grid: { display: false }, border: { display: false }, title: { display: true, text: "Cumul" } },
        },
      },
    });
  }
  const seriesCategorie = d => d.par_categorie.series.map(s => ({ label: s.label, data: s.data, backgroundColor: COULEUR[s.key], borderRadius: 4, maxBarThickness: 46 }));
  const seriesEvolution = d => [
    { type: "bar", label: "Produits ajoutés", data: d.evolution.ajoutes, backgroundColor: SERIE_2, borderRadius: 6, maxBarThickness: 34, yAxisID: "y" },
    { type: "line", label: "Total cumulé", data: d.evolution.cumul, borderColor: SERIE_1, backgroundColor: SERIE_1, borderWidth: 2, pointRadius: 4, tension: .3, cubicInterpolationMode: "monotone", yAxisID: "y1" },
  ];
  function majGraphiques(d) {
    if (!graphiques.etat) return;
    graphiques.etat.data.labels = d.par_etat.labels;
    graphiques.etat.data.datasets[0].data = d.par_etat.data;
    graphiques.categorie.data.labels = d.par_categorie.labels;
    graphiques.categorie.data.datasets = seriesCategorie(d);
    graphiques.evolution.data.labels = d.evolution.labels;
    graphiques.evolution.data.datasets = seriesEvolution(d);
    Object.values(graphiques).forEach(g => g.update());
  }

  /* ---------------- Rendu global + rafraîchissement ---------------- */
  const compteur = (s, v) => { const n = document.querySelector(s); if (n) n.textContent = v; };
  function rendre(d) {
    const k = { total: d.total, disponibles: d.compteurs.disponibles, ruptures: d.compteurs.ruptures, archives: d.compteurs.archives,
                valeur_stock: Math.round(d.valeur_stock), prix_moyen: d.prix_moyen.toFixed(2), ce_mois: d.ce_mois, nb_categories: d.nb_categories };
    Object.entries(k).forEach(([cle, v]) => compteur(`[data-kpi="${cle}"]`, v));
  }

  const stamp = document.createElement("span");
  stamp.className = "pr-stamp muted small";
  const barre = document.querySelector(".pr-bo-tabs");
  if (barre) barre.appendChild(stamp);
  const heure = () => new Date().toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  stamp.textContent = "Données à jour : " + heure();

  let derniere = JSON.stringify(JSON.parse(brut.textContent));
  async function rafraichir() {
    if (!URL_DONNEES || document.hidden) return;
    try {
      const r = await fetch(URL_DONNEES, { cache: "no-store", headers: { Accept: "application/json" } });
      if (!r.ok) return;
      const d = await r.json();
      stamp.textContent = "Données à jour : " + heure();
      const signature = JSON.stringify(d);
      if (signature === derniere) return;
      derniere = signature;
      if ((d.total > 0) !== aDesGraphiques) { window.location.reload(); return; }   // bascule vide / non vide
      rendre(d);
      majGraphiques(d);
    } catch (e) { /* hors ligne : on réessaiera */ }
  }

  const initial = JSON.parse(brut.textContent);
  creerGraphiques(initial);

  setInterval(rafraichir, INTERVALLE_MS);
  document.addEventListener("visibilitychange", rafraichir);
  window.addEventListener("focus", rafraichir);
})();
