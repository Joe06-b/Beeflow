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
  const champs = { categorie: el("categorie_produit"), quantite: el("quantite"), prix: el("prix"), etat: el("etat") };
  if (!champs.quantite || !champs.prix || !champs.etat) return;

  const regles = {};            // panneau « Avant d'enregistrer » : texte d'aide statique, pas d'état
  const msg = null;
  const modeModification = false;
  const touche = new Set();            // champs que l'utilisateur a déjà manipulés
  let tentative = false;               // true après une tentative d'enregistrement

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
    if (!li || li.classList.contains("is-" + etat)) return;
    li.classList.remove("is-neutral", "is-valid", "is-invalid");
    li.classList.add("is-" + etat);
  }

  const manque = nom => (touche.has(nom) || tentative) ? "invalid" : "neutral";

  /* ---- évaluation de toutes les règles ---- */
  function evaluer() {
    const q = nombre(champs.quantite);
    const p = nombre(champs.prix);
    const e = champs.etat.value;
    const cat = champs.categorie ? champs.categorie.value : "x";

    const qOk = q !== null && !Number.isNaN(q);
    const pOk = p !== null && !Number.isNaN(p);
    const qNeg = qOk && q < 0 || Number.isNaN(q);
    const pNeg = pOk && p < 0 || Number.isNaN(p);

    // Règles du panneau
    etatRegle("disponible", e !== "disponible" || !qOk || qNeg ? "neutral" : (q > 0 ? "valid" : "invalid"));
    etatRegle("rupture", e !== "rupture_stock" || !qOk || qNeg ? "neutral" : (q === 0 ? "valid" : "invalid"));
    etatRegle("positifs", qNeg || pNeg ? "invalid" : (qOk || pOk ? "valid" : "neutral"));

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

    const bloquant = !!erreurQ || !!erreurE || pNeg || !qOk || !pOk || cat === "";
    // EAN-13 : toujours généré par le serveur ; il est « prêt » dès que le formulaire est valide
    etatRegle("ean", modeModification || !bloquant ? "valid" : "neutral");
    if (!bloquant && msg) msg.hidden = true;
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
    const premier = form.querySelector(".field.is-invalid input, .field.is-invalid select");
    if (premier) premier.focus();
  });

  evaluer();
})();
