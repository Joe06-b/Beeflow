/* ==========================================================================
   BeeFlow – Suivi sanitaire : notification sonore des alertes
   - Interroge /suivis/alertes/compte/ (JSON)
   - Affiche une carte en bas à droite + joue un son si un contrôle est
     en retard ou prévu dans les 7 jours
   - Le son n'est joué qu'une fois par session (sauf si une nouvelle alerte arrive)
   - Bouton son activé / coupé (mémorisé dans le navigateur)
   ========================================================================== */
(function () {
  "use strict";

  const config = document.getElementById("ss-notif-config");
  if (!config) return;

  const URL_COMPTE = config.dataset.urlCompte;
  const URL_ALERTES = config.dataset.urlAlertes;
  const ICONS = document.body.dataset.icons || "/static/img/icons.svg";
  const INTERVALLE_MS = 5 * 60 * 1000;          // nouvelle vérification toutes les 5 minutes
  const CLE_MUET = "beeflow_alertes_muet";
  const CLE_DEJA_SONNE = "beeflow_alertes_signature";
  const CLE_FERMEE = "beeflow_alertes_fermee";      // la carte a été fermée pour ces alertes-là

  const icon = (name, cls) => `<svg class="ico ${cls || ""}" aria-hidden="true"><use href="${ICONS}#${name}"></use></svg>`;
  function lire(stockage, cle) { try { return stockage.getItem(cle); } catch (e) { return null; } }
  function ecrire(stockage, cle, val) { try { stockage.setItem(cle, val); } catch (e) { /* ignoré */ } }

  /* ---- Son : généré avec la Web Audio API (aucun fichier audio) ---- */
  let audioCtx = null;

  function bip(frequence, debut, duree) {
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.type = "sine";
    osc.frequency.value = frequence;
    const t = audioCtx.currentTime + debut;
    gain.gain.setValueAtTime(0.0001, t);
    gain.gain.exponentialRampToValueAtTime(0.35, t + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.0001, t + duree);
    osc.connect(gain).connect(audioCtx.destination);
    osc.start(t);
    osc.stop(t + duree + 0.05);
  }

  function jouerSon(urgent) {
    if (lire(localStorage, CLE_MUET) === "1") return;
    try { audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)(); }
    catch (e) { return; }

    const lancer = () => {
      if (urgent) { bip(880, 0, 0.18); bip(880, 0.25, 0.18); bip(1046, 0.5, 0.3); }   // retard : 3 bips
      else { bip(660, 0, 0.2); bip(880, 0.28, 0.3); }                                   // proche : 2 bips
    };

    if (audioCtx.state === "suspended") {
      // Le navigateur bloque le son tant que l'utilisateur n'a pas cliqué : on attend le premier geste.
      const debloquer = () => {
        audioCtx.resume().then(lancer);
        document.removeEventListener("click", debloquer);
        document.removeEventListener("keydown", debloquer);
      };
      audioCtx.resume().then(() => { if (audioCtx.state === "running") lancer(); else throw 0; })
        .catch(() => {
          document.addEventListener("click", debloquer, { once: true });
          document.addEventListener("keydown", debloquer, { once: true });
        });
    } else {
      lancer();
    }
  }

  /* ---- Carte de notification ---- */
  function message(d) {
    const parties = [];
    if (d.en_retard) parties.push(`<strong>${d.en_retard}</strong> contrôle${d.en_retard > 1 ? "s" : ""} en retard`);
    if (d.aujourdhui) parties.push(`<strong>${d.aujourdhui}</strong> prévu${d.aujourdhui > 1 ? "s" : ""} aujourd'hui`);
    const autres = d.proches - d.aujourdhui;
    if (autres > 0) parties.push(`<strong>${autres}</strong> dans les ${d.jours} prochains jours`);
    return parties.join(", ");
  }

  function boutonSon(btn) {
    const muet = lire(localStorage, CLE_MUET) === "1";
    btn.innerHTML = icon(muet ? "volume-off" : "volume");
    btn.title = muet ? "Activer le son" : "Couper le son";
    btn.setAttribute("aria-label", btn.title);
  }

  function afficher(d, urgent) {
    let b = document.getElementById("ss-notif");
    if (!b) {
      b = document.createElement("aside");
      b.id = "ss-notif";
      b.setAttribute("role", "alert");
      document.body.appendChild(b);
    }
    b.className = "ss-notif " + (urgent ? "is-urgent" : "is-soon");
    b.innerHTML = `
      <span class="hex ss-notif-icon">${icon(urgent ? "alert" : "bell")}</span>
      <div class="ss-notif-body">
        <strong>${urgent ? "Contrôle sanitaire en retard" : "Contrôle sanitaire à venir"}</strong>
        <p>${message(d)}.</p>
        <a href="${URL_ALERTES}" class="btn btn-link">Voir les alertes ${icon("arrow-right", "ico-sm")}</a>
      </div>
      <div class="ss-notif-tools">
        <button type="button" class="icon-btn" data-son></button>
        <button type="button" class="icon-btn" data-fermer title="Fermer" aria-label="Fermer">${icon("x")}</button>
      </div>`;

    const son = b.querySelector("[data-son]");
    boutonSon(son);
    son.onclick = () => {
      const muet = lire(localStorage, CLE_MUET) !== "1";
      ecrire(localStorage, CLE_MUET, muet ? "1" : "0");
      boutonSon(son);
      if (!muet) jouerSon(urgent);            // petit aperçu quand on réactive le son
    };
    // Fermer = ne plus l'afficher pendant cette session, tant qu'aucune NOUVELLE alerte n'arrive
    b.querySelector("[data-fermer]").onclick = () => {
      ecrire(sessionStorage, CLE_FERMEE, b.dataset.signature);
      b.classList.add("is-leaving");
      setTimeout(() => b.remove(), 250);
    };
  }

  /* ---- Vérification ---- */
  async function verifier() {
    let d;
    try {
      const rep = await fetch(URL_COMPTE, { headers: { Accept: "application/json" } });
      if (!rep.ok) return;
      d = await rep.json();
    } catch (e) { return; }

    if (!d.en_retard && !d.proches) {
      const b = document.getElementById("ss-notif");
      if (b) b.remove();
      return;
    }

    const urgent = d.en_retard > 0;
    const signature = `${d.en_retard}-${d.proches}`;
    if (lire(sessionStorage, CLE_FERMEE) === signature) return;   // déjà vue et fermée
    afficher(d, urgent);
    document.getElementById("ss-notif").dataset.signature = signature;

    if (lire(sessionStorage, CLE_DEJA_SONNE) !== signature) {
      ecrire(sessionStorage, CLE_DEJA_SONNE, signature);
      jouerSon(urgent);
    }
  }

  verifier();
  setInterval(verifier, INTERVALLE_MS);
})();
