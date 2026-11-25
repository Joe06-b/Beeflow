/* ==========================================================================
   BeeFlow – Gestion des produits : validation en temps réel (front + back office)
   - Chaque champ concerné : gris (pas encore évalué) / vert (règle respectée) / rouge (non respectée)
   - L'enregistrement est bloqué tant qu'une règle obligatoire n'est pas respectée
     (le serveur revalide de toute façon : Produit.clean()).
   ========================================================================== */
(function () {
  "use strict";

  const form = document.getElementById("produit-form");
  const panel = document.getElementById("pr-regles");
  if (!form) return;

  const el = n => form.elements[n];
  const champs = { categorie: el("categorie_produit"), stock: el("stock"), quantite: el("quantite"), volume: el("volume_stockage"), prix: el("prix"), etat: el("etat") };
  if (!champs.quantite || !champs.prix || !champs.etat) return;

  const regles = {};            // panneau « Avant d'enregistrer » : une entrée par data-rule
  if (panel) panel.querySelectorAll("[data-rule]").forEach(li => { regles[li.dataset.rule] = li; });
  const score = document.getElementById("prRulesScore");
  const msg = document.getElementById("prRulesMsg");
  const modeModification = form.dataset.mode === "modification";
  const touche = new Set();            // champs que l'utilisateur a déjà manipulés
  let tentative = false;               // true après une tentative d'enregistrement

    /* ---- stocks proposés : type compatible + non plein + place suffisante (m³) ---- */
  const optionsStock = champs.stock ? Array.from(champs.stock.options).map(o => ({
    value: o.value, text: o.textContent,
    restant: o.dataset.restant === undefined ? null : Number(o.dataset.restant),
    type: o.dataset.type || null,
  })) : [];
  let stockRetire = false;

    function filtrerStocks(vol) {
    const select = champs.stock;
    if (!select) return;
    const cat = champs.categorie ? champs.categorie.value : "";
    const besoin = vol !== null && !Number.isNaN(vol) && vol > 0 ? vol : 0;
    const courant = select.value;
    select.innerHTML = "";
    optionsStock.forEach(o => {
      if (o.value !== "") {
        if (cat !== "" && o.type !== null && o.type !== cat) return;                           // type incompatible
        if (o.restant !== null && (o.restant <= 0 || o.restant < besoin * (1 - 1e-9))) return; // plein ou trop petit
      }
      select.add(new Option(o.text, o.value, false, o.value === courant));
    });
    if (select.options.length === 1 && optionsStock.length > 1) select.options[0].textContent = "— Aucun stock compatible —";
    if (courant !== "" && select.value !== courant) { stockRetire = true; touche.add("stock"); }
    else if (select.value !== "") stockRetire = false;
  }

  /* ---- utilitaires ---- */
  function nombre(input) {
    const v = (input.value || "").trim().replace(",", ".");
    if (v === "") return null;
    const n = Number(v);
    return Number.isFinite(n) ? n : NaN;
  }

  function etatChamp(nom, etat, texte) {
    const input = champs[nom];
    const wrap = input && input.closest(".field");
    if (!wrap) return;
    wrap.classList.remove("is-neutral", "is-valid", "is-invalid");
    wrap.classList.add("is-" + etat);
    let live = wrap.querySelector(".pr-live");
    if (etat === "invalid" && texte) {
      if (!live) {
        live = document.createElement("small");
        live.className = "field-error pr-live";
        live.setAttribute("role", "alert");
        wrap.appendChild(live);
      }
      live.textContent = texte;
    } else if (live) {
      live.remove();
    }
    input.setAttribute("aria-invalid", etat === "invalid" ? "true" : "false");
  }

  function etatRegle(nom, etat) {
    const li = regles[nom];
    if (!li) return;
    li.classList.remove("is-ok", "is-pending", "is-bad");
    li.classList.add("is-" + etat);
  }

  const manque = nom => (touche.has(nom) || tentative) ? "invalid" : "neutral";

  /* ---- évaluation de toutes les règles ---- */
  function evaluer() {
    const q = nombre(champs.quantite);
    const v = champs.volume ? nombre(champs.volume) : null;
    filtrerStocks(v);
    const p = nombre(champs.prix);
    const e = champs.etat.value;
    const cat = champs.categorie ? champs.categorie.value : "x";
    const stk = champs.stock ? champs.stock.value : "x";

    const qOk = q !== null && !Number.isNaN(q);
    const pOk = p !== null && !Number.isNaN(p);
    const qNeg = qOk && q < 0 || Number.isNaN(q);
    const pNeg = pOk && p < 0 || Number.isNaN(p);

    // Règles du panneau
    etatRegle("categorie", cat === "" ? "pending" : "ok");
    etatRegle("stock", stk === "" ? "pending" : "ok");
    etatRegle("quantite", !qOk && !qNeg ? "pending" : (qNeg ? "bad" : "ok"));
    etatRegle("prix", !pOk && !pNeg ? "pending" : (pNeg ? "bad" : "ok"));
    const incoherent = qOk && !qNeg && ((e === "disponible" && q === 0) || (e === "rupture_stock" && q > 0));
    etatRegle("etat", incoherent ? "bad" : (qOk && !qNeg ? "ok" : "pending"));

    // Champs
    let erreurQ = null;
    if (qNeg) erreurQ = "La quantité ne peut pas être négative.";
    else if (qOk && e === "disponible" && q === 0) erreurQ = "Un produit disponible doit avoir une quantité supérieure à 0.";
    else if (qOk && e === "rupture_stock" && q > 0) erreurQ = "Un produit en rupture de stock doit avoir une quantité égale à 0.";
    if (erreurQ) etatChamp("quantite", "invalid", erreurQ);
    else if (!qOk) etatChamp("quantite", manque("quantite"), "Champ obligatoire.");
    else etatChamp("quantite", "valid");

    if (pNeg) etatChamp("prix", "invalid", "Le prix ne peut pas être négatif.");
    else if (!pOk) etatChamp("prix", manque("prix"), "Champ obligatoire.");
    else etatChamp("prix", "valid");

    let erreurE = null;
    if (qOk && !qNeg) {
      if (e === "disponible" && q <= 0) erreurE = "Disponible : la quantité doit être supérieure à 0.";
      if (e === "rupture_stock" && q > 0) erreurE = "Rupture de stock : la quantité doit être égale à 0.";
    }
    if (erreurE) etatChamp("etat", "invalid", erreurE);
    else etatChamp("etat", qOk && !qNeg ? "valid" : "neutral");

    if (champs.categorie) {
      if (cat === "") etatChamp("categorie", manque("categorie"), "Champ obligatoire.");
      else etatChamp("categorie", "valid");
    }

    if (champs.stock) {
      if (stk === "") etatChamp("stock", manque("stock"), stockRetire
        ? "Ce stock n'est plus compatible (type ou capacité). Choisissez-en un autre."
        : "Champ obligatoire.");
      else etatChamp("stock", "valid");
    }
    
    const volKo = !!champs.volume && (v === null || Number.isNaN(v) || v < 0 || (qOk && q > 0 && v === 0));
    if (champs.volume) {
      if (v === null) etatChamp("volume", manque("volume"), "Champ obligatoire.");
      else if (Number.isNaN(v) || v < 0) etatChamp("volume", "invalid", "Le volume de stockage ne peut pas être négatif.");
      else if (qOk && q > 0 && v === 0) etatChamp("volume", "invalid", "Le volume doit être supérieur à 0 quand la quantité est supérieure à 0.");
      else etatChamp("volume", "valid");
    }
    const bloquant = volKo || !!erreurQ || !!erreurE || pNeg || !qOk || !pOk || cat === "" || stk === "";
    // EAN-13 : toujours généré par le serveur ; il est « prêt » dès que le formulaire est valide
    etatRegle("ean", modeModification || !bloquant ? "ok" : "pending");
    if (!bloquant && msg) msg.hidden = true;
    const items = Object.values(regles);
    const ok = items.filter(li => li.classList.contains("is-ok")).length;
    if (score) {
      score.textContent = ok ? ok + "/" + items.length : "";
      score.className = "pr-rules-score" + (ok === items.length ? " is-complete" : "");
    }
    if (panel) panel.classList.toggle("is-complete", ok === items.length);
    return !bloquant;
  }

  /* ---- événements ---- */
  Object.entries(champs).forEach(([nom, input]) => {
    if (!input) return;
    const maj = () => {
      touche.add(nom);
      const wrap = input.closest(".field");
      if (wrap) {                                   // l'utilisateur corrige : on retire l'erreur serveur
        wrap.classList.remove("has-error");
        wrap.querySelectorAll(".field-error:not(.pr-live)").forEach(n => { n.hidden = true; });
      }
      evaluer();
    };
    input.addEventListener("input", maj);
    input.addEventListener("change", maj);
    input.addEventListener("blur", () => { touche.add(nom); evaluer(); });
  });

  form.addEventListener("submit", e => {
    tentative = true;
    if (evaluer()) return;
    e.preventDefault();
    if (msg) {
      msg.textContent = "Corrigez les règles en rouge ou les champs obligatoires avant d'enregistrer.";
      msg.hidden = false;
    }
    const fautive = panel && panel.querySelector("li.is-bad");
    if (fautive) { fautive.classList.remove("shake"); void fautive.offsetWidth; fautive.classList.add("shake"); }
    const premier = form.querySelector(".field.is-invalid input, .field.is-invalid select");
    if (premier) premier.focus();
  });

  evaluer();
})();
