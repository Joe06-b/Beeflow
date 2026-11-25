(function () {
  "use strict";

  const vueCartes = document.getElementById("prVueCartes");
  const vue3d = document.getElementById("prVue3d");
  const boutons = document.querySelectorAll("[data-pr-vue]");
  const erreur = document.getElementById("pr3dError");
  if (!vueCartes || !vue3d || !boutons.length) return;

  let etagere = null;
  let chargement = false;

  function afficher(mode) {
    const en3d = mode === "etagere";
    vueCartes.hidden = en3d;
    vue3d.hidden = !en3d;
    boutons.forEach(b => b.setAttribute("aria-pressed", String(b.dataset.prVue === mode)));
    try { sessionStorage.setItem("pr_vue", mode); } catch (e) { /* stockage indisponible */ }
    if (en3d) ouvrir(); else if (etagere) etagere.pause();
  }

  async function ouvrir() {
    if (etagere) { etagere.reprendre(); return; }
    if (chargement) return;
    chargement = true;
    vue3d.classList.add("is-loading");
    try {
      const THREE = await import("three");
      const { OrbitControls } = await import("three/addons/controls/OrbitControls.js");
      etagere = construire(THREE, OrbitControls);
      if (erreur) erreur.hidden = true;
    } catch (err) {
      console.error("Étagère 3D indisponible :", err);
      if (erreur) erreur.hidden = false;
      afficher("cartes");
    } finally {
      chargement = false;
      vue3d.classList.remove("is-loading");
    }
  }

  boutons.forEach(b => b.addEventListener("click", () => afficher(b.dataset.prVue)));
  document.addEventListener("visibilitychange", () => {
    if (!etagere) return;
    if (document.hidden) etagere.pause();
    else if (!vue3d.hidden) etagere.reprendre();
  });

  let memo = null;
  try { memo = sessionStorage.getItem("pr_vue"); } catch (e) { /* ignoré */ }
  if (memo === "etagere") afficher("etagere");

  /* ------------------------------------------------------------------------
     Lecture des produits (liste HTML cachée)
     ------------------------------------------------------------------------ */
  function lireProduits() {
    const nombre = v => { const n = parseFloat(String(v || "").replace(",", ".")); return Number.isFinite(n) ? n : 0; };
    return Array.from(document.querySelectorAll("#pr3dData li")).map(li => {
      const d = li.dataset;
      return {
        id: d.id, cat: d.cat, catLabel: d.catLabel, nom: d.nom || "",
        qte: nombre(d.qte), vol: nombre(d.vol), unite: d.unite, etat: d.etat, etatLabel: d.etatLabel,
        prix: d.prix, stockId: d.stockId || "", stockNom: d.stockNom || "", cap: nombre(d.cap),
        url: d.url, urlModif: d.urlModif,
      };
    });
  }

  /* ------------------------------------------------------------------------
     Scène 3D
     ------------------------------------------------------------------------ */
  function construire(THREE, OrbitControls) {
    const holder = document.getElementById("pr3dCanvas");
    const tip = document.getElementById("pr3dTip");
    const info = document.getElementById("pr3dInfo");
    const reduit = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const produits = lireProduits();

    const PALETTE = {
      miel:         { liq: 0xE9A820, top: 0xF7D77A, bulle: 0xFFE9A8 },
      pollen:       { liq: 0xE88A1A, top: 0xF5B455, bulle: 0xB5600B },
      propolis:     { liq: 0x7B4A1F, top: 0xA9702F, bulle: 0xC89A5E },
      gelee_royale: { liq: 0xF0DDA6, top: 0xFAF0CC, bulle: 0xFFFFFF },
      cire:         { liq: 0xEBCB63, top: 0xF6E39A, bulle: 0xFFF3C4 },
    };
    const UNITES = { kg: "kg", g: "g", l: "L", ml: "ml", unite: "unité(s)" };
    const BASE = { kg: 1, g: 0.001, l: 1, ml: 0.001, unite: 1 };
    const fmt = n => String(Math.round(n * 100) / 100).replace(".", ",");
    const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
    const easeOutCubic = u => 1 - Math.pow(1 - u, 3);
    const easeInOut = u => (u < 0.5 ? 4 * u * u * u : 1 - Math.pow(-2 * u + 2, 3) / 2);
    const easeOutBounce = u => {
      const n = 7.5625, d = 2.75;
      if (u < 1 / d) return n * u * u;
      if (u < 2 / d) { u -= 1.5 / d; return n * u * u + 0.75; }
      if (u < 2.5 / d) { u -= 2.25 / d; return n * u * u + 0.9375; }
      u -= 2.625 / d; return n * u * u + 0.984375;
    };
    const hasard = (a, b) => { const x = Math.sin(a * 127.1 + b * 311.7) * 43758.5453; return x - Math.floor(x); };

    /* ---- rendu ---- */
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(36, 1, 0.1, 100);
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.05;
    holder.appendChild(renderer.domElement);

    /* ---- textures dessinées en canvas (aucune image externe) ---- */
    function canvasTex(w, h, dessiner) {
      const c = document.createElement("canvas");
      c.width = w; c.height = h;
      dessiner(c.getContext("2d"), w, h);
      const t = new THREE.CanvasTexture(c);
      t.colorSpace = THREE.SRGBColorSpace;
      t.anisotropy = 4;
      return t;
    }
    function hexPath(g, cx, cy, r) {
      g.beginPath();
      for (let i = 0; i < 6; i++) {
        const a = Math.PI / 3 * i + Math.PI / 6;
        const x = cx + r * Math.cos(a), y = cy + r * Math.sin(a);
        if (i === 0) g.moveTo(x, y); else g.lineTo(x, y);
      }
      g.closePath();
    }
    function hexMur() {
      const r = 64, dx = r * Math.sqrt(3), dy = r * 1.5;
      const w = Math.round(dx * 9), h = Math.round(dy * 10);
      const tex = canvasTex(w, h, (g) => {
        const fond = g.createLinearGradient(0, 0, 0, h);
        fond.addColorStop(0, "#4A2F19"); fond.addColorStop(1, "#33200F");
        g.fillStyle = fond; g.fillRect(0, 0, w, h);
        for (let row = -1; row <= 10; row++) {
          for (let col = -1; col <= 9; col++) {
            const cx = col * dx + (((row % 2) + 2) % 2 ? dx / 2 : 0), cy = row * dy;
            const k = hasard(((col % 9) + 9) % 9, ((row % 10) + 10) % 10);
            hexPath(g, cx, cy, r - 3);
            g.fillStyle = "rgba(233,185,73," + (0.04 + k * 0.2).toFixed(3) + ")"; g.fill();
            g.lineWidth = 3; g.strokeStyle = "rgba(233,185,73,.26)"; g.stroke();
          }
        }
      });
      tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
      return tex;
    }
    function bois(clair) {
      const tex = canvasTex(512, 128, (g, w, h) => {
        g.fillStyle = clair ? "#A9743D" : "#6E4421"; g.fillRect(0, 0, w, h);
        for (let i = 0; i < 46; i++) {
          g.strokeStyle = "rgba(" + (clair ? "60,34,12" : "30,16,6") + "," + (0.08 + hasard(i, 3) * 0.2).toFixed(2) + ")";
          g.lineWidth = 1 + hasard(i, 5) * 2;
          const y = hasard(i, 1) * h;
          g.beginPath(); g.moveTo(0, y);
          g.bezierCurveTo(w * 0.3, y + (hasard(i, 7) - 0.5) * 10, w * 0.7, y + (hasard(i, 9) - 0.5) * 10, w, y);
          g.stroke();
        }
      });
      tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
      return tex;
    }

    /* ---- disposition de l'étagère ---- */
    const n = produits.length;
    const parRang = Math.max(1, Math.min(5, n));
    const rangs = Math.max(1, Math.ceil(n / parRang));
    const PAS_X = 1.55, PAS_Y = 2.15;
    const W = Math.max(parRang * PAS_X + 0.9, 3.4);
    const yMax = 1.95, yMin = -(rangs - 1) * PAS_Y - 0.3;
    const H = yMax - yMin, cy = (yMax + yMin) / 2;
    const rangY = r => -r * PAS_Y;

    /* ---- lumières ---- */
    scene.add(new THREE.HemisphereLight(0xFFF3DA, 0x6B4423, 1.5));
    const soleil = new THREE.DirectionalLight(0xFFE3B0, 2.4);
    soleil.position.set(-W * 0.5 - 2, cy + H * 0.6 + 3, 7);
    soleil.target.position.set(0, cy, 0);
    soleil.castShadow = true;
    soleil.shadow.mapSize.set(2048, 2048);
    Object.assign(soleil.shadow.camera, { left: -(W / 2 + 2), right: W / 2 + 2, top: H / 2 + 2, bottom: -(H / 2 + 2), near: 1, far: 30 });
    soleil.shadow.bias = -0.0005; soleil.shadow.normalBias = 0.02;
    scene.add(soleil, soleil.target);
    const chaud = new THREE.PointLight(0xFFB347, 30, 14);
    chaud.position.set(W / 2, cy, 4.5);
    scene.add(chaud);

    /* ---- meuble : mur d'alvéoles, montants, planches ---- */
    const texMur = hexMur();
    texMur.repeat.set((W + 0.4) / 6, H / 6);
    const mur = new THREE.Mesh(new THREE.PlaneGeometry(W + 0.4, H), new THREE.MeshStandardMaterial({ map: texMur, roughness: 0.95 }));
    mur.position.set(0, cy, -0.75);
    mur.receiveShadow = true;
    scene.add(mur);

    const matBoisClair = new THREE.MeshStandardMaterial({ map: bois(true), roughness: 0.7 });
    const matBoisSombre = new THREE.MeshStandardMaterial({ map: bois(false), roughness: 0.8 });
    const planche = (w, h, d, mat, x, y, z) => {
      const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat);
      m.position.set(x, y, z); m.castShadow = true; m.receiveShadow = true; scene.add(m); return m;
    };
    for (let r = 0; r < rangs; r++) planche(W, 0.14, 1.3, matBoisClair, 0, rangY(r) - 0.07, -0.05);
    planche(0.2, H + 0.3, 1.4, matBoisSombre, -(W / 2 + 0.1), cy, -0.05);
    planche(0.2, H + 0.3, 1.4, matBoisSombre, W / 2 + 0.1, cy, -0.05);
    planche(W + 0.7, 0.22, 1.5, matBoisSombre, 0, yMax + 0.1, -0.05);
    planche(W + 0.7, 0.28, 1.5, matBoisSombre, 0, yMin - 0.14, -0.05);

    /* ---- pots ---- */
    const profil = [[0, 0], [0.42, 0], [0.49, 0.05], [0.5, 0.12], [0.5, 0.92], [0.47, 1.0], [0.4, 1.07], [0.37, 1.13], [0.37, 1.2]]
      .map(([x, y]) => new THREE.Vector2(x, y));
    const geoVerre = new THREE.LatheGeometry(profil, 40);
    const geoLiquide = new THREE.CylinderGeometry(0.465, 0.465, 1, 40, 1, false);
    geoLiquide.translate(0, 0.5, 0);
    const geoSurface = new THREE.CircleGeometry(0.465, 40);
    geoSurface.rotateX(-Math.PI / 2);
    const geoCouvercle = new THREE.CylinderGeometry(0.4, 0.4, 0.16, 36);
    const geoBague = new THREE.TorusGeometry(0.4, 0.025, 8, 36);
    geoBague.rotateX(Math.PI / 2);
    const geoBulle = new THREE.SphereGeometry(1, 8, 8);
    const geoReflet = new THREE.PlaneGeometry(0.07, 0.8);
    const HL = 0.9, FOND = 0.06;

    function etiquette(p, couleur) {
      const hex = "#" + couleur.toString(16).padStart(6, "0");
      const ajuste = (g, texte, x, y, maxW, taille, poids, align) => {
        let t = taille;
        g.font = poids + " " + t + "px Georgia, serif";
        while (g.measureText(texte).width > maxW && t > 12) { t -= 2; g.font = poids + " " + t + "px Georgia, serif"; }
        g.textAlign = align || "left";
        g.fillText(texte, x, y);
      };
      return canvasTex(512, 276, (g, w, h) => {
        g.fillStyle = "#FBF3E0"; g.fillRect(0, 0, w, h);
        g.strokeStyle = "#C98A1E"; g.lineWidth = 6; g.strokeRect(10, 10, w - 20, h - 20);
        hexPath(g, 74, 76, 38); g.fillStyle = hex; g.fill(); g.lineWidth = 4; g.strokeStyle = "#7A4E12"; g.stroke();
        g.fillStyle = "#2B1B0F";
        ajuste(g, p.catLabel, 130, 76, 350, 46, "700");
        g.fillStyle = "#6B4A22";
        ajuste(g, p.nom || "—", 130, 112, 350, 28, "600");
        g.fillStyle = "#C98A1E"; g.fillRect(36, 128, w - 72, 3);
        g.fillStyle = "#2B1B0F";
        ajuste(g, fmt(p.qte) + " " + (UNITES[p.unite] || p.unite), 36, 184, 440, 50, "700");
        g.fillStyle = "#6B4A22";
        ajuste(g, "Produit #" + p.id, 36, 222, 200, 28, "600");
        ajuste(g, p.stockId ? "Stock #" + p.stockId : "Sans stock", w - 36, 222, 220, 28, "700", "right");
        g.fillStyle = p.etat === "rupture_stock" ? "#A93C30" : (p.etat === "archive" ? "#6B6B6B" : "#3F7A4A");
        g.fillRect(10, 238, w - 20, 28);
        g.fillStyle = "#FFFFFF";
        ajuste(g, String(p.etatLabel).toUpperCase(), w / 2, 259, w - 60, 20, "700", "center");
      });
    }

    const maxSansStock = Math.max(0, ...produits.filter(p => !(p.cap > 0)).map(p => p.vol));
    const pots = [];
    const cibles = [];

    produits.forEach((p, i) => {
        const pal = PALETTE[p.cat] || PALETTE.miel;
        const rang = Math.floor(i / parRang), col = i % parRang;
        const x = (col - (parRang - 1) / 2) * PAS_X;
        const base = rangY(rang);
        const rupture = p.etat === "rupture_stock", archive = p.etat === "archive";

      const occup = p.cap > 0 ? clamp(p.vol / p.cap, 0, 1) : 0;   // part réelle du stock (m³)
    let fill = p.cap > 0 ? p.vol / p.cap : (maxSansStock > 0 ? p.vol / maxSansStock : 0);
    fill = clamp(fill, 0, 1);
    if (p.qte > 0) fill = Math.max(fill, 0.08);                  // niveau visuel minimum
    if (rupture) fill = 0;

      const groupe = new THREE.Group();
      groupe.position.set(x, base, 0.1);
      groupe.rotation.y = ((i % 3) - 1) * 0.12;
      scene.add(groupe);

      const teinte = archive ? new THREE.Color(pal.liq).multiplyScalar(0.5) : new THREE.Color(pal.liq);
      const liquide = new THREE.Mesh(geoLiquide, new THREE.MeshPhysicalMaterial({
        color: teinte, roughness: 0.18, clearcoat: 0.6, emissive: teinte, emissiveIntensity: 0.14,
      }));
      liquide.position.y = FOND; liquide.castShadow = true;
      groupe.add(liquide);

      const pivot = new THREE.Object3D();
      groupe.add(pivot);
      const surface = new THREE.Mesh(geoSurface, new THREE.MeshStandardMaterial({
        color: archive ? new THREE.Color(pal.top).multiplyScalar(0.55) : pal.top, roughness: 0.2, metalness: 0.1,
      }));
      surface.position.y = 0.003;
      pivot.add(surface);

      const verre = new THREE.Mesh(geoVerre, new THREE.MeshPhysicalMaterial({
        color: archive ? 0x2A2018 : (rupture ? 0xCFD6DC : 0xFFFFFF),
        transparent: true, opacity: archive ? 0.5 : 0.2, roughness: 0.04,
        clearcoat: 1, clearcoatRoughness: 0.05, side: THREE.DoubleSide, depthWrite: false,
      }));
      verre.renderOrder = 2;
      groupe.add(verre);

      const matCouvercle = new THREE.MeshStandardMaterial({ color: archive ? 0x4A3A2A : 0xC98A1E, metalness: 0.6, roughness: 0.35 });
      const couvercle = new THREE.Mesh(geoCouvercle, matCouvercle);
      couvercle.position.y = 1.28; couvercle.castShadow = true;
      const bague = new THREE.Mesh(geoBague, matCouvercle);
      bague.position.y = 1.2;
      groupe.add(couvercle, bague);

      const papier = new THREE.Mesh(
        new THREE.CylinderGeometry(0.508, 0.508, 0.52, 32, 1, true, -0.95, 1.9),
        new THREE.MeshStandardMaterial({ map: etiquette(p, pal.liq), roughness: 0.9 }));
      papier.position.y = 0.5; papier.renderOrder = 3;
      groupe.add(papier);

      const reflet = new THREE.Mesh(geoReflet, new THREE.MeshBasicMaterial({
        color: 0xFFFFFF, transparent: true, opacity: 0.35, blending: THREE.AdditiveBlending, depthWrite: false,
      }));
      reflet.position.set(-0.395, 0.62, 0.315); reflet.rotation.y = -0.9; reflet.renderOrder = 4;
      groupe.add(reflet);

      const matBulle = new THREE.MeshBasicMaterial({ color: pal.bulle, transparent: true, opacity: 0.55, depthWrite: false });
      const bulles = [];
      for (let k = 0; k < 6; k++) {
        const m = new THREE.Mesh(geoBulle, matBulle);
        const r = 0.018 + hasard(i, k + 20) * 0.022;
        m.scale.setScalar(p.cat === "pollen" ? r * 1.3 : r);
        groupe.add(m);
        bulles.push({ m, ph: hasard(i, k + 40), sp: (0.1 + hasard(i, k + 60) * 0.18) * (p.cat === "pollen" ? 0.4 : 1), a: 0.1 + hasard(i, k + 80) * 0.25, ph2: hasard(i, k + 100) * 6.28 });
      }

      const pot = { p, groupe, liquide, pivot, bulles, x, base, fill, occup, niveau: 0, lift: 0, hover: false, phase: hasard(i, 7) * 6.28, depart: 0.25 + i * 0.13 };
      [verre, couvercle, papier].forEach(m => { m.userData.pot = pot; cibles.push(m); });
      pots.push(pot);
    });

    /* ---- abeilles ---- */
    function creerAbeille(echelle) {
      const g = new THREE.Group();
      const jaune = new THREE.MeshStandardMaterial({ color: 0xF2B72A, roughness: 0.5 });
      const noir = new THREE.MeshStandardMaterial({ color: 0x2B1B0F, roughness: 0.6 });
      const corps = new THREE.Mesh(new THREE.SphereGeometry(0.5, 20, 16), jaune);
      corps.scale.set(0.8, 0.8, 1.2);
      g.add(corps);
      [[-0.15, 0.36], [0.25, 0.33]].forEach(([z, r]) => {
        const b = new THREE.Mesh(new THREE.TorusGeometry(r, 0.06, 8, 24), noir);
        b.position.z = z; g.add(b);
      });
      const tete = new THREE.Mesh(new THREE.SphereGeometry(0.26, 16, 12), noir);
      tete.position.z = 0.7; g.add(tete);
      const dard = new THREE.Mesh(new THREE.ConeGeometry(0.09, 0.25, 8), noir);
      dard.rotation.x = -Math.PI / 2; dard.position.z = -0.7; g.add(dard);
      const matAile = new THREE.MeshBasicMaterial({ color: 0xFFFFFF, transparent: true, opacity: 0.6, side: THREE.DoubleSide, depthWrite: false });
      const ailes = [-1, 1].map(s => {
        const pv = new THREE.Object3D();
        pv.position.set(s * 0.15, 0.36, 0.1);
        const a = new THREE.Mesh(new THREE.SphereGeometry(0.5, 12, 8), matAile);
        a.scale.set(0.9, 0.05, 0.4); a.position.x = s * 0.4;
        pv.add(a); g.add(pv);
        return { pv, s };
      });
      g.scale.setScalar(echelle);
      scene.add(g);
      return { g, ailes };
    }
    const abeilles = [
      { ...creerAbeille(0.3), fx: 0.31, fy: 0.5, fz: 0.77, p: 0 },
      { ...creerAbeille(0.24), fx: 0.23, fy: 0.41, fz: 0.63, p: 2.4 },
    ];
    const cheminAbeille = (b, t) => ({
      x: Math.sin(t * b.fx + b.p) * (W / 2 + 0.5),
      y: cy + Math.sin(t * b.fy + b.p * 1.7) * (H / 2) * 0.8,
      z: 1.5 + Math.sin(t * b.fz + b.p) * 0.45,
    });

    /* ---- paillettes dorées ---- */
    const NB = 110;
    const posP = new Float32Array(NB * 3);
    const bw = W + 3, bh = H + 2;
    for (let i = 0; i < NB; i++) {
      posP[i * 3] = (hasard(i, 1) - 0.5) * bw;
      posP[i * 3 + 1] = cy + (hasard(i, 2) - 0.5) * bh;
      posP[i * 3 + 2] = -0.4 + hasard(i, 3) * 3;
    }
    const geoP = new THREE.BufferGeometry();
    geoP.setAttribute("position", new THREE.BufferAttribute(posP, 3));
    scene.add(new THREE.Points(geoP, new THREE.PointsMaterial({
      color: 0xFFD36B, size: 0.06, transparent: true, opacity: 0.8, depthWrite: false, blending: THREE.AdditiveBlending,
    })));

    /* ---- caméra et contrôles ---- */
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true; controls.dampingFactor = 0.08; controls.enablePan = false;
    controls.minDistance = 2.5;
    controls.minPolarAngle = 1.0; controls.maxPolarAngle = 1.8;
    controls.minAzimuthAngle = -0.9; controls.maxAzimuthAngle = 0.9;
    let dist = 12, selection = null, anim = null;

    function cadrer() {
      const w = holder.clientWidth || 800, h = holder.clientHeight || 520;
      renderer.setSize(w, h, false);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      const demi = Math.tan(THREE.MathUtils.degToRad(camera.fov) / 2);
      dist = Math.max((H + 0.8) / (2 * demi), (W + 1.6) / (2 * demi * camera.aspect)) + 0.9;
      controls.maxDistance = dist * 1.4;
      if (!selection && !anim) { camera.position.set(0, cy, dist); controls.target.set(0, cy, 0); }
    }
    function aller(pos, cible) {
      const de = { pos: camera.position.clone(), cible: controls.target.clone() };
      if (reduit) { camera.position.copy(pos); controls.target.copy(cible); return; }
      anim = { t: 0, dur: 1.1, de, pos, cible };
    }
    controls.addEventListener("start", () => { anim = null; });

    /* ---- fiche d'un pot ---- */
    const el = (tag, cls, texte) => { const e = document.createElement(tag); if (cls) e.className = cls; if (texte != null) e.textContent = texte; return e; };
    function ouvrirFiche(pot) {
      const p = pot.p;
      const bloc = [];
      const t = el("div", "pr3d-info-titre");
      t.append(el("strong", "", p.catLabel + (p.nom ? " · " + p.nom : "")), el("span", "pr3d-badge is-" + p.etat, p.etatLabel));
      bloc.push(t);
      const ligne = (a, b) => { const l = el("p", "pr3d-ligne"); l.append(el("span", "", a), el("strong", "", b)); return l; };
      bloc.push(ligne("Produit", "#" + p.id));
      bloc.push(ligne("Quantité", fmt(p.qte) + " " + (UNITES[p.unite] || p.unite)));
      bloc.push(ligne("Prix", p.prix + " TND"));
      bloc.push(ligne("Stock", p.stockId ? "#" + p.stockId + " – " + p.stockNom : "Aucun stock affecté"));
      if (p.cap > 0) bloc.push(ligne("Occupe", (Math.round(pot.occup * 1000) / 10) + " % du stock"));
      const act = el("div", "pr3d-info-actions");
      const consulter = el("a", "btn btn-honey btn-sm", "Consulter"); consulter.href = p.url;
      const modifier = el("a", "btn btn-ghost btn-sm", "Modifier"); modifier.href = p.urlModif;
      const retour = el("button", "btn btn-ghost btn-sm", "Retour à l'étagère"); retour.type = "button";
      retour.addEventListener("click", reinitialiser);
      act.append(consulter, modifier, retour);
      bloc.push(act);
      info.replaceChildren(...bloc);
      info.hidden = false;
    }
    function choisir(pot) {
      selection = pot;
      tip.hidden = true;
      aller(new THREE.Vector3(pot.x, pot.base + 0.85, 3.7), new THREE.Vector3(pot.x, pot.base + 0.65, 0));
      ouvrirFiche(pot);
    }
    function reinitialiser() {
      selection = null; info.hidden = true;
      aller(new THREE.Vector3(0, cy, dist), new THREE.Vector3(0, cy, 0));
    }

    /* ---- souris, toucher, clavier ---- */
    const rayon = new THREE.Raycaster();
    const ptr = new THREE.Vector2();
    let ptrBouge = false, ptrType = "mouse", ptrX = 0, ptrY = 0, survol = null, bas = null;

    function viser(e) {
      const r = renderer.domElement.getBoundingClientRect();
      ptr.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
      rayon.setFromCamera(ptr, camera);
      const hit = rayon.intersectObjects(cibles, false)[0];
      return hit ? hit.object.userData.pot : null;
    }
    renderer.domElement.addEventListener("pointermove", e => { ptrBouge = true; ptrType = e.pointerType; ptrX = e.clientX; ptrY = e.clientY; });
    renderer.domElement.addEventListener("pointerleave", () => { survol = null; ptrBouge = false; tip.hidden = true; renderer.domElement.style.cursor = ""; });
    renderer.domElement.addEventListener("pointerdown", e => { bas = { x: e.clientX, y: e.clientY, t: performance.now() }; });
    renderer.domElement.addEventListener("pointerup", e => {
      if (!bas) return;
      const court = Math.hypot(e.clientX - bas.x, e.clientY - bas.y) < 6 && performance.now() - bas.t < 500;
      bas = null;
      if (!court) return;
      const pot = viser(e);
      if (pot) choisir(pot); else if (selection) reinitialiser();
    });
    holder.tabIndex = 0;
    holder.addEventListener("keydown", e => {
      if (e.key === "Escape" && selection) { reinitialiser(); return; }
      if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
      e.preventDefault();
      const i = selection ? pots.indexOf(selection) : -1;
      const pas = e.key === "ArrowRight" ? 1 : -1;
      choisir(pots[(i + pas + pots.length) % pots.length]);
    });

    function majSurvol() {
      if (!ptrBouge) return;
      ptrBouge = false;
      survol = anim ? null : viser({ clientX: ptrX, clientY: ptrY });
      renderer.domElement.style.cursor = survol ? "pointer" : "";
      if (survol && ptrType === "mouse" && survol !== selection) {
        const p = survol.p, r = holder.getBoundingClientRect();
        const l1 = el("strong", "", p.catLabel + (p.nom ? " · " + p.nom : ""));
        const l2 = el("span", "", "#" + p.id + " · " + fmt(p.qte) + " " + (UNITES[p.unite] || p.unite) + " · " + (p.stockId ? "Stock #" + p.stockId : "Sans stock"));
        const l3 = el("em", "", "Cliquez pour zoomer");
        tip.replaceChildren(l1, l2, l3);
        tip.style.left = Math.min(ptrX - r.left + 16, r.width - 190) + "px";
        tip.style.top = (ptrY - r.top + 16) + "px";
        tip.hidden = false;
      } else tip.hidden = true;
    }

    /* ---- boucle d'animation ---- */
    let actif = false, raf = 0, temps = 0, derniere = 0;
    function image(now) {
      if (!actif) { raf = 0; return; }
      raf = requestAnimationFrame(image);
      const dt = Math.min(0.05, (now - derniere) / 1000);
      derniere = now; temps += dt;

      pots.forEach(pot => {
        const u = reduit ? 1 : clamp((temps - pot.depart) / 0.9, 0, 1);
        const v = reduit ? 1 : clamp((temps - pot.depart - 0.5) / 1.5, 0, 1);
        pot.niveau = easeOutCubic(v) * pot.fill;
        const levee = (pot.hover = survol === pot) || selection === pot ? 0.16 : 0;
        pot.lift += (levee - pot.lift) * Math.min(1, dt * 8);
        pot.groupe.position.y = pot.base + (1 - easeOutBounce(u)) * 3.2 + pot.lift;
        pot.groupe.visible = u > 0;
        const h = HL * pot.niveau;
        pot.liquide.scale.y = Math.max(h, 0.0001);
        pot.liquide.visible = h > 0.01;
        pot.pivot.visible = h > 0.01;
        pot.pivot.position.y = FOND + h;
        const amp = Math.min(1, h * 1.4) * (1 + (pot.lift > 0.02 ? 0.8 : 0));
        pot.pivot.rotation.x = Math.sin(temps * 1.6 + pot.phase) * 0.035 * amp;
        pot.pivot.rotation.z = Math.cos(temps * 1.3 + pot.phase) * 0.03 * amp;
        pot.bulles.forEach(b => {
          b.m.visible = h > 0.12;
          if (!b.m.visible) return;
          const f = (temps * b.sp + b.ph) % 1;
          b.m.position.set(Math.cos(temps * 0.9 + b.ph2) * b.a, FOND + 0.04 + f * (h - 0.08), Math.sin(temps * 0.9 + b.ph2) * b.a);
        });
      });

      abeilles.forEach(b => {
        const a = cheminAbeille(b, temps), s = cheminAbeille(b, temps + 0.05);
        b.g.position.set(a.x, a.y + Math.sin(temps * 9 + b.p) * 0.03, a.z);
        b.g.lookAt(s.x, s.y, s.z);
        b.ailes.forEach(w => { w.pv.rotation.z = w.s * (0.25 + Math.sin(temps * 70 + b.p) * 0.55); });
      });

      for (let i = 0; i < NB; i++) {
        posP[i * 3 + 1] += dt * (0.08 + hasard(i, 4) * 0.12);
        posP[i * 3] += Math.sin(temps * 0.6 + i) * dt * 0.05;
        if (posP[i * 3 + 1] > cy + bh / 2) posP[i * 3 + 1] = cy - bh / 2;
      }
      geoP.attributes.position.needsUpdate = true;

      if (anim) {
        anim.t += dt;
        const k = easeInOut(clamp(anim.t / anim.dur, 0, 1));
        camera.position.lerpVectors(anim.de.pos, anim.pos, k);
        controls.target.lerpVectors(anim.de.cible, anim.cible, k);
        if (anim.t >= anim.dur) anim = null;
      }
      majSurvol();
      controls.update();
      renderer.render(scene, camera);
    }
    function reprendre() {
      cadrer();
      if (actif) return;
      actif = true; derniere = performance.now();
      raf = requestAnimationFrame(image);
    }
    function pause() { actif = false; if (raf) cancelAnimationFrame(raf); raf = 0; }

    if (typeof ResizeObserver !== "undefined") new ResizeObserver(() => { if (actif) cadrer(); }).observe(holder);
    reprendre();
    return { pause, reprendre };
  }
})();