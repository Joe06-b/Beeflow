/* ==========================================================================
   SUIVI SANITAIRE — Vérification EN DIRECT des règles « Avant d'enregistrer »
   Chaque règle a 4 états :
     idle     (gris)  pas encore concernée
     pending  (ambre) commencée mais incomplète
     ok       (vert)  respectée  → zoom + coche + petit son
     bad      (rouge) non respectée → secousse + son grave, champs concernés en rouge
   Mêmes règles que SuiviSanitaire.clean() côté serveur (le serveur vérifie toujours).
   ========================================================================== */
(function () {
    "use strict";

    const panel = document.getElementById("regles");
    const form = panel && document.getElementById(panel.dataset.form);
    if (!form) return;

    const $ = name => form.elements[name];
    const val = name => ($(name) ? $(name).value.trim() : "");
    const date = name => { const v = val(name); return v ? new Date(v + "T00:00:00") : null; };
    const today = () => { const d = new Date(); d.setHours(0, 0, 0, 0); return d; };
    const icon = (n, c) => window.BeeFlow ? BeeFlow.icon(n, c) : "";
    const sfx = n => window.BeeFlow && BeeFlow.sfx.play(n);

    /* Chaque règle renvoie { etat, msg, champs } */
    const REGLES = {
        date() {
            const d = date("date_suivi");
            if (!d) return { etat: "idle" };
            if (d > today()) return { etat: "bad", msg: "La date choisie est dans le futur.", champs: ["date_suivi"] };
            return { etat: "ok" };
        },
        traitement() {
            const type = val("type_traitement"), dose = val("dose"), dt = date("date_traitement"), ds = date("date_suivi");
            if (!type && !dose && !dt) return { etat: "idle" };
            if (dt && ds && dt < ds) return { etat: "bad", msg: "Le traitement est daté avant le suivi.", champs: ["date_traitement"] };
            if (type && dose && dt) return { etat: "ok" };
            const manque = [];
            if (!type) manque.push("le produit");
            if (!dose) manque.push("la dose");
            if (!dt) manque.push("la date");
            return { etat: "pending", msg: "Il manque " + manque.join(" et ") + ".", champs: [] };
        },
        controle() {
            const ds = date("date_suivi"), dc = date("date_prochain_controle");
            if (!dc) return { etat: "idle" };
            if (!ds) return { etat: "pending", msg: "Choisissez d'abord la date du suivi." };
            if (dc <= ds) return { etat: "bad", msg: "Le contrôle doit être après le " + ds.toLocaleDateString("fr-FR") + ".", champs: ["date_prochain_controle"] };
            return { etat: "ok" };
        },
        risque() {
            const etat = val("etat_sante"), risque = val("niveau_risque");
            if (!etat || !risque) return { etat: "idle" };
            if (etat === "Critique" && risque === "Faible") return { etat: "bad", msg: "Choisissez un risque moyen ou élevé.", champs: ["niveau_risque"] };
            return { etat: "ok" };
        },
    };

    const ICONES = { ok: "check", bad: "x", pending: "clock" };
    const items = Array.from(panel.querySelectorAll("[data-rule]"));
    const previous = {};
    const score = document.getElementById("reglesScore");
    let premierPassage = true;

    function marquerChamps() {
        form.querySelectorAll(".field.is-rule-bad").forEach(f => f.classList.remove("is-rule-bad"));
    }

    function evaluer() {
        marquerChamps();
        let ok = 0, actives = 0, sonOk = false, sonKo = false;

        items.forEach(li => {
            const nom = li.dataset.rule;
            const r = REGLES[nom]();
            const avant = previous[nom];

            li.classList.remove("is-idle", "is-pending", "is-ok", "is-bad");
            li.classList.add("is-" + r.etat);
            li.querySelector(".ss-rule-icon").innerHTML = icon(ICONES[r.etat] || li.dataset.icon, "ico-sm");

            // message d'aide sous la règle
            let aide = li.querySelector(".ss-rule-help");
            if (r.msg && r.etat !== "ok") {
                if (!aide) { aide = document.createElement("small"); aide.className = "ss-rule-help"; li.querySelector(".ss-rule-text").appendChild(aide); }
                aide.textContent = r.msg;
            } else if (aide) aide.remove();

            // champs concernés en rouge
            (r.etat === "bad" ? r.champs || [] : []).forEach(n => {
                const champ = $(n) && $(n).closest(".field");
                if (champ) champ.classList.add("is-rule-bad");
            });

            // animation + son seulement quand l'état change (et pas au chargement)
            if (!premierPassage && avant !== r.etat) {
                li.classList.remove("pop", "shake"); void li.offsetWidth;
                if (r.etat === "ok") { li.classList.add("pop"); sonOk = true; }
                if (r.etat === "bad") { li.classList.add("shake"); sonKo = true; }
            }
            previous[nom] = r.etat;
            if (r.etat !== "idle") actives++;
            if (r.etat === "ok") ok++;
        });

        if (sonKo) sfx("regleKo"); else if (sonOk) sfx("regleOk");
        score.textContent = actives ? `${ok}/${items.length}` : "";
        score.className = "ss-rules-score" + (ok === items.length ? " is-complete" : "");
        panel.classList.toggle("is-complete", ok === items.length);
        premierPassage = false;
    }

    form.addEventListener("input", () => evaluer());
    form.addEventListener("change", () => evaluer());
    evaluer();

    /* ------------------------------------------------------------------
       AJOUT : si on quitte la page SANS enregistrer, les champs sont vidés.
       Sans cela, le bouton « Retour » du navigateur (ou le cache de page)
       réaffiche le formulaire à moitié rempli.
       form.reset() remet chaque champ à sa valeur d'origine (celle envoyée
       par le serveur : vide, ou la ruche pré-choisie). Le mode modification
       n'est pas concerné.
       ------------------------------------------------------------------ */
    if (form.hasAttribute("data-vider-si-abandon")) {
        let envoi = false;
        // écouté sur document : passe APRÈS le contrôle des règles, donc on sait si l'envoi a été bloqué
        document.addEventListener("submit", e => { if (e.target === form && !e.defaultPrevented) envoi = true; });

        const vider = () => {
            form.reset();
            Object.keys(previous).forEach(k => delete previous[k]);
            premierPassage = true;            // pas d'animation ni de son pendant la remise à zéro
            evaluer();
        };
        // En quittant la page (lien, Annuler, Retour, fermeture d'onglet) sans avoir enregistré
        window.addEventListener("pagehide", () => { if (!envoi) vider(); });
        // En revenant sur la page par « Retour » / « Suivant » : on repart d'un formulaire vierge
        window.addEventListener("pageshow", e => {
            const nav = performance.getEntriesByType && performance.getEntriesByType("navigation")[0];
            if (e.persisted || (nav && nav.type === "back_forward")) { envoi = false; vider(); }
        });
    }

    // Envoi : si une règle est rouge, on bloque et on montre la règle (le serveur vérifie de toute façon)
    form.addEventListener("submit", e => {
        evaluer();
        const fautive = panel.querySelector("li.is-bad");
        if (fautive) {
            e.preventDefault();
            sfx("erreur");
            fautive.classList.remove("shake"); void fautive.offsetWidth; fautive.classList.add("shake");
            fautive.scrollIntoView({ behavior: "smooth", block: "center" });
            window.BeeFlow && BeeFlow.toast("Corrigez la règle en rouge avant d'enregistrer.", "error");
        }
    });
})();
