/* ==========================================================================
   ÉVOLUTION DANS LA RUCHE — cadre de couvain en 3D (Three.js, module ES)
   La « 4e dimension » est le temps : à chaque semaine, les cellules changent
   (vague qui part du centre du couvain), les abeilles sont plus ou moins
   nombreuses, et les signes de la maladie apparaissent ou disparaissent.
   La simulation vient d'evolution.js (window.EVO + évènement « evo:etat »).
   ========================================================================== */
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

window.EVO3D_OK = true;                       // le module a bien démarré (filet de sécurité du template)
const EVO = window.EVO;
const D = EVO.data, SLUG = D.slug, P0 = D.population, T = D.traitement.semaine;
const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

const viewer = document.getElementById("evoViewer");
const holder = document.getElementById("evoCanvas");

/* ------------------------------------------------------------------------
   États possibles d'une cellule
   ------------------------------------------------------------------------ */
const ETATS = {
    miel:      { label: "Miel",                     c: "#D89A1C", h: 0.15 },
    pollen:    { label: "Pollen",                   c: "#D99A35", h: 0.09 },
    opercule:  { label: "Couvain operculé",         c: "#C38E4C", h: 0.17 },
    larve:     { label: "Jeune larve",              c: "#F2E8D8", h: 0.07 },
    vide:      { label: "Cellule vide",             c: "#4A2E18", h: 0.01 },
    neuve:     { label: "Cire neuve",               c: "#EBCB7A", h: 0.01 },
    perce:     { label: "Opercule percé",           c: "#A77A43", h: 0.165, trou: true },
    affaisse:  { label: "Opercule affaissé, percé", c: "#5A3A1F", h: 0.11, trou: true },
    tordue:    { label: "Larve tordue, jaunie",     c: "#C9A04A", h: 0.07 },
    momie:     { label: "Larve momifiée",           c: "#E6E3DA", h: 0.185 },
    galerie:   { label: "Galeries de larves",       c: "#8C7A58", h: 0.06 },
    fermente:  { label: "Miel qui fermente",        c: "#B8A579", h: 0.13 },
};
const POLLENS = ["#E3A13A", "#C9792A", "#D7B547", "#B5652A"];

// Signe principal de la maladie sur le couvain
const MALADE = {
    "varroase": "perce", "loque-americaine": "affaisse", "loque-europeenne": "tordue",
    "couvain-platre": "momie", "petit-coleoptere": "galerie",
}[SLUG];

// Légende (cellules + signes visibles sur les abeilles)
const legende = ["miel", "pollen", "opercule", "larve", "vide"].map(k => ({ c: ETATS[k].c, l: ETATS[k].label }));
if (MALADE) legende.push({ c: ETATS[MALADE].c, l: ETATS[MALADE].label, hit: true });
if (SLUG === "petit-coleoptere") legende.push({ c: ETATS.fermente.c, l: ETATS.fermente.label, hit: true }, { c: "#2E1C0C", l: "Coléoptère", hit: true });
if (SLUG === "loque-americaine") legende.push({ c: ETATS.neuve.c, l: "Cire neuve (après transvasement)" });
if (SLUG === "varroase") legende.push({ c: "#8E2F12", l: "Varroa sur une abeille", hit: true });
if (SLUG === "varroase" || SLUG === "ailes-deformees") legende.push({ c: "#9A958C", l: "Abeille aux ailes froissées", hit: true });
if (SLUG === "nosemose") legende.push({ c: "#6B4A1F", l: "Traces de diarrhée", hit: true });
if (SLUG === "frelon-asiatique") legende.push({ c: "#D9731E", l: "Frelon asiatique", hit: true });
document.getElementById("evoLegend").innerHTML = legende
    .map(x => `<li${x.hit ? ' class="is-hit"' : ""}><i style="background:${x.c}"></i>${x.l}</li>`).join("");

// On laisse le navigateur afficher la page AVANT de préparer la 3D
await new Promise(r => requestAnimationFrame(() => setTimeout(r, 0)));

/* ------------------------------------------------------------------------
   Moteur
   ------------------------------------------------------------------------ */
let renderer;
try {
    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
} catch (e) {
    document.getElementById("evoLoading").hidden = true;
    document.getElementById("evoFallback").hidden = false;
    throw e;
}
renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.05;
holder.appendChild(renderer.domElement);

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(36, 1, 0.05, 100);
const HOME = { pos: new THREE.Vector3(1.4, 0.45, 10.2), target: new THREE.Vector3(0.55, -0.05, 0) };
camera.position.copy(HOME.pos);

const controls = new OrbitControls(camera, renderer.domElement);
controls.target.copy(HOME.target);
controls.enableDamping = true;
controls.dampingFactor = 0.08;
controls.enablePan = false;
controls.minDistance = 2.2;
controls.maxDistance = 11;
controls.minAzimuthAngle = -1.15;
controls.maxAzimuthAngle = 1.15;
controls.minPolarAngle = 0.75;
controls.maxPolarAngle = 2.3;

scene.add(new THREE.HemisphereLight(0xfff3d6, 0x3a2414, 1.2));
const key = new THREE.DirectionalLight(0xfff1d0, 2.2);
key.position.set(3, 4, 6);
scene.add(key);
const rim = new THREE.PointLight(0xe9b949, 16, 14);
rim.position.set(-4, 2, 3);
scene.add(rim);

/* ------------------------------------------------------------------------
   Outils : hexagone, fusion de formes avec couleurs par sommet
   ------------------------------------------------------------------------ */
const R = 0.13;                                  // rayon d'une cellule (centre → sommet)
const W_STEP = Math.sqrt(3) * R, H_STEP = 1.5 * R;
const COLS = 26, ROWS = 17;
const W = COLS * W_STEP + W_STEP / 2, H = (ROWS - 1) * H_STEP + 2 * R;

function hexShape(r) {
    const s = new THREE.Shape();
    for (let k = 0; k < 6; k++) {
        const a = Math.PI / 2 + k * Math.PI / 3;
        k ? s.lineTo(r * Math.cos(a), r * Math.sin(a)) : s.moveTo(r * Math.cos(a), r * Math.sin(a));
    }
    s.closePath();
    return s;
}

function fusion(parts) {
    const pos = [], nor = [], col = [], idx = [];
    let off = 0;
    parts.forEach(({ geo, couleur }) => {
        const p = geo.attributes.position, n = geo.attributes.normal;
        for (let i = 0; i < p.count; i++) {
            pos.push(p.getX(i), p.getY(i), p.getZ(i));
            nor.push(n.getX(i), n.getY(i), n.getZ(i));
            const c = typeof couleur === "function" ? couleur(p.getX(i), p.getY(i), p.getZ(i)) : couleur;
            col.push(c.r, c.g, c.b);
        }
        (geo.index ? Array.from(geo.index.array) : [...Array(p.count).keys()]).forEach(i => idx.push(i + off));
        off += p.count;
    });
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
    g.setAttribute("normal", new THREE.Float32BufferAttribute(nor, 3));
    g.setAttribute("color", new THREE.Float32BufferAttribute(col, 3));
    g.setIndex(idx);
    return g;
}
const C = hex => new THREE.Color(hex);
const ellipse = (sx, sy, sz, x = 0, y = 0, z = 0, seg = 14) => new THREE.SphereGeometry(1, seg, Math.ceil(seg * 0.7)).scale(sx, sy, sz).translate(x, y, z);

// Petit générateur aléatoire reproductible : le cadre est le même à chaque visite
let graine = 1234567;
const alea = () => ((graine = (graine * 16807) % 2147483647) / 2147483647);

/* ------------------------------------------------------------------------
   Cadre en bois + rayon de cire
   ------------------------------------------------------------------------ */
const bois = new THREE.MeshStandardMaterial({ color: 0xb98a55, roughness: 0.8 });
const cadre = new THREE.Group();
const barre = (w, h, d, x, y) => { const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), bois); m.position.set(x, y, 0); cadre.add(m); };
barre(W + 1.3, 0.2, 0.5, 0, H / 2 + 0.12);       // tête de cadre (avec oreilles)
barre(0.16, H + 0.1, 0.42, -W / 2 - 0.09, 0);
barre(0.16, H + 0.1, 0.42, W / 2 + 0.09, 0);
barre(W + 0.34, 0.12, 0.42, 0, -H / 2 - 0.08);
scene.add(cadre);

const fond = new THREE.Mesh(new THREE.BoxGeometry(W, H, 0.04), new THREE.MeshStandardMaterial({ color: 0x5a3a1c, roughness: 0.9 }));
fond.position.z = -0.02;
scene.add(fond);

// Cellules : positions + tirages fixes
const cellules = [];
for (let r = 0; r < ROWS; r++) {
    for (let c = 0; c < COLS; c++) {
        const x = -W / 2 + W_STEP / 2 + c * W_STEP + (r % 2 ? W_STEP / 2 : 0);
        const y = H / 2 - R - r * H_STEP;
        const xn = x / (W / 2), yn = y / (H / 2);
        const d = Math.hypot(xn / 1.0, (yn + 0.12) / 0.86);
        cellules.push({ x, y, xn, yn, d, u1: alea(), u2: alea(), u3: alea(), delai: d * 0.7 + alea() * 0.12 });
    }
}
const N = cellules.length;

const murGeo = new THREE.ExtrudeGeometry((() => { const s = hexShape(R); s.holes.push(hexShape(R * 0.85)); return s; })(), { depth: 1, bevelEnabled: false });
const contGeo = new THREE.ExtrudeGeometry(hexShape(R * 0.86), { depth: 1, bevelEnabled: false });
const murs = new THREE.InstancedMesh(murGeo, new THREE.MeshStandardMaterial({ color: 0xe8c271, roughness: 0.55 }), N);
const contenus = new THREE.InstancedMesh(contGeo, new THREE.MeshStandardMaterial({ roughness: 0.42, metalness: 0.05 }), N);
const trous = new THREE.InstancedMesh(new THREE.CircleGeometry(R * 0.24, 10), new THREE.MeshStandardMaterial({ color: 0x1e1209, roughness: 0.9 }), N);
scene.add(murs, contenus, trous);

/* ------------------------------------------------------------------------
   Abeilles, frelons, coléoptères, taches, varroas
   ------------------------------------------------------------------------ */
const abeilleGeo = fusion([
    { geo: ellipse(0.13, 0.075, 0.068, -0.1, 0, 0), couleur: x => (Math.sin((x + 0.1) * 62) > 0.25 ? C("#2B1B0F") : C("#D8962A")) },
    { geo: ellipse(0.068, 0.062, 0.06, 0.035, 0, 0.005), couleur: C("#8A5A2B") },
    { geo: ellipse(0.045, 0.052, 0.045, 0.115, 0, 0), couleur: C("#22150B") },
]);
const ailesGeo = fusion([
    { geo: ellipse(0.11, 0.042, 0.004, -0.045, 0.07, 0.07, 10).rotateZ(0.0), couleur: C("#FFFFFF") },
    { geo: ellipse(0.11, 0.042, 0.004, -0.045, -0.07, 0.07, 10), couleur: C("#FFFFFF") },
]);
const NB_ABEILLES = 40;
const abeilles = new THREE.InstancedMesh(abeilleGeo, new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.6 }), NB_ABEILLES);
const ailes = new THREE.InstancedMesh(ailesGeo, new THREE.MeshStandardMaterial({ color: 0xffffff, transparent: true, opacity: 0.6, roughness: 0.2, depthWrite: false }), NB_ABEILLES);
const varroas = new THREE.InstancedMesh(ellipse(0.028, 0.034, 0.014, 0, 0, 0, 10), new THREE.MeshStandardMaterial({ color: 0x8e2f12, roughness: 0.35 }), NB_ABEILLES);
scene.add(abeilles, ailes, varroas);

const bees = Array.from({ length: NB_ABEILLES }, (_, i) => ({
    x: (alea() - 0.5) * (W - 0.4), y: (alea() - 0.5) * (H - 0.4), h: alea() * Math.PI * 2,
    v: 0.12 + alea() * 0.12, pause: 0, vis: 0, rang: alea(), aile: 1, aileC: new THREE.Color(1, 1, 1),
}));

// Coléoptères
const NB_COLEO = 45;
const coleos = new THREE.InstancedMesh(fusion([
    { geo: ellipse(0.075, 0.048, 0.03, 0, 0, 0), couleur: C("#2E1C0C") },
    { geo: ellipse(0.03, 0.036, 0.022, 0.08, 0, 0), couleur: C("#1A0F06") },
]), new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.3, metalness: 0.2 }), NB_COLEO);
const beetles = Array.from({ length: NB_COLEO }, () => ({ x: (alea() - 0.5) * (W - 0.3), y: (alea() - 0.5) * (H - 0.3), h: alea() * 6.28, rang: alea(), vis: 0 }));
if (SLUG === "petit-coleoptere") scene.add(coleos);

// Taches de diarrhée (nosémose)
const NB_TACHES = 80;
const taches = new THREE.InstancedMesh(new THREE.CircleGeometry(1, 9), new THREE.MeshStandardMaterial({ color: 0x6b4a1f, roughness: 0.9 }), NB_TACHES);
const spots = Array.from({ length: NB_TACHES }, (_, i) => ({
    x: (alea() - 0.5) * W, y: i < 14 ? H / 2 + 0.12 : (alea() - 0.5) * H, z: i < 14 ? 0.255 : 0.172,
    s: 0.018 + alea() * 0.03, rang: alea(), vis: 0,
}));
if (SLUG === "nosemose") scene.add(taches);

// Frelons
const frelonGeo = fusion([
    { geo: ellipse(0.22, 0.12, 0.12, -0.16, 0, 0), couleur: x => (Math.sin((x + 0.16) * 30) > 0.1 ? C("#D9731E") : C("#1C120A")) },
    { geo: ellipse(0.11, 0.1, 0.1, 0.06, 0, 0), couleur: C("#1C120A") },
    { geo: ellipse(0.075, 0.09, 0.08, 0.19, 0, 0), couleur: C("#E39A2B") },
]);
const frelonAileMat = new THREE.MeshStandardMaterial({ color: 0x8a6a3a, transparent: true, opacity: 0.55, side: THREE.DoubleSide, depthWrite: false });
const frelons = [];
if (SLUG === "frelon-asiatique") {
    for (let i = 0; i < 4; i++) {
        // le corps est modélisé « couché » (avant = x, dessus = z) : on le redresse, puis on le tourne vers le cadre
        const g = new THREE.Group(), corps = new THREE.Group();
        corps.rotation.x = -Math.PI / 2;
        corps.add(new THREE.Mesh(frelonGeo, new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.5 })));
        const a1 = new THREE.Mesh(ellipse(0.2, 0.06, 0.005, -0.1, 0, 0, 10), frelonAileMat);
        const a2 = a1.clone();
        a1.position.set(0.04, 0.08, 0.08); a2.position.set(0.04, -0.08, 0.08);
        corps.add(a1, a2);
        g.add(corps);
        g.userData = { a1, a2, phase: i * 1.7, cx: -1.8 + i * 1.2, cy: -0.6 + (i % 2) * 1.1, vis: 0, rang: i / 4 };
        g.scale.setScalar(0.001);
        scene.add(g);
        frelons.push(g);
    }
}

/* ------------------------------------------------------------------------
   Calcul de l'état de chaque cellule pour une semaine donnée
   ------------------------------------------------------------------------ */
function etatCellule(c, p, scenario, t) {
    const I = p.I, ratio = Math.min(1.15, Math.max(0.08, p.P / P0));
    const apresTransvasement = EVO.transvasement && scenario === "avec" && t >= T;
    let rayon = 0.64 * Math.pow(ratio, 0.75);

    if (apresTransvasement) {
        const age = t - T;
        if (age < 2) return "neuve";
        rayon = 0.64 * Math.min(1, (age - 1) / 5);
        if (c.d < rayon) return c.u2 < 0.6 ? "opercule" : "larve";
        if (c.d < rayon + 0.12 && age > 3) return "pollen";
        return c.yn > 0.55 && c.u1 < (age - 2) / 8 ? "miel" : "neuve";
    }

    if (c.d < rayon) {
        const base = c.u2 < 0.72 ? "opercule" : "larve";
        if (D.cible === "couvain" && MALADE) {
            if (c.u1 < I * 0.95) {
                if (I > 0.45 && c.u3 < (I - 0.45) * 1.25) return "vide";        // larves mortes, sorties par les ouvrières
                if (MALADE === "tordue" || MALADE === "galerie") return MALADE;
                return base === "opercule" || MALADE === "momie" ? MALADE : base;
            }
        } else if (c.u1 < I * (D.cible === "butineuses" ? 0.25 : 0.38)) {
            return "vide";                                                      // la reine pond moins : couvain lacunaire
        }
        return base;
    }
    if (c.d < rayon + 0.2) {
        if (D.cible === "butineuses" && c.u1 < I * 1.1) return "vide";
        if (SLUG === "petit-coleoptere" && c.u1 < I * 0.8) return "fermente";
        return "pollen";
    }
    if (c.yn < -0.5 && Math.abs(c.xn) > 0.62) return "vide";
    if (D.cible === "butineuses" && c.u1 < I * 0.7) return "vide";
    if (SLUG === "petit-coleoptere" && c.u1 < I * 0.9) return "fermente";
    return "miel";
}

/* ------------------------------------------------------------------------
   Transitions : chaque cellule passe de son ancien état au nouveau,
   en vague depuis le centre du couvain
   ------------------------------------------------------------------------ */
const cur = cellules.map(() => ({ col: new THREE.Color("#4A2E18"), h: 0.01, mur: 0.17, trou: 0 }));
const from = cellules.map(() => ({ col: new THREE.Color(), h: 0, mur: 0, trou: 0 }));
const to = cellules.map(() => ({ col: new THREE.Color(), h: 0, mur: 0, trou: 0, etat: "" }));
let tau = 99, tauFin = 0;

let cible = { abeilles: 0, malades: 0, varroas: 0, coleos: 0, taches: 0, frelons: 0 };

function appliquer({ semaine, scenario, point }, instantane) {
    cellules.forEach((c, i) => {
        const e = etatCellule(c, point, scenario, semaine);
        const def = ETATS[e];
        from[i].col.copy(cur[i].col); from[i].h = cur[i].h; from[i].mur = cur[i].mur; from[i].trou = cur[i].trou;
        to[i].etat = e;
        to[i].col.set(e === "pollen" ? POLLENS[Math.floor(c.u3 * 4)] : e === "momie" && c.u3 < 0.45 ? "#A3A39B" : def.c);
        // petite variation de teinte pour un rendu naturel
        to[i].col.offsetHSL(0, 0, (c.u2 - 0.5) * 0.05);
        to[i].h = def.h;
        to[i].mur = e === "neuve" ? 0.035 : 0.17;
        to[i].trou = def.trou ? 1 : 0;
    });
    tau = instantane || reduceMotion ? 99 : 0;
    tauFin = Math.max(...cellules.map(c => c.delai)) + 0.5;

    const I = point.I, ratio = Math.min(1.15, point.P / P0);
    cible = {
        abeilles: Math.round(NB_ABEILLES * Math.min(1, ratio * 0.9)),
        malades: ["varroase", "ailes-deformees"].includes(SLUG) ? Math.max(0, SLUG === "varroase" ? (I - 0.35) * 1.3 : I * 0.9) : 0,
        varroas: SLUG === "varroase" ? I * 0.55 : 0,
        coleos: SLUG === "petit-coleoptere" ? Math.round(NB_COLEO * I) : 0,
        taches: SLUG === "nosemose" ? Math.round(NB_TACHES * Math.min(1, I * 1.15)) : 0,
        frelons: SLUG === "frelon-asiatique" ? Math.min(4, Math.ceil(I * 5.5)) : 0,
    };
    if (instantane) majCellules(true);
}

const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), v = new THREE.Vector3(), sc = new THREE.Vector3();
const AXE_Z = new THREE.Vector3(0, 0, 1);
const lisse = x => x * x * (3 - 2 * x);

function majCellules(force) {
    if (tau > tauFin + 0.1 && !force) return;
    cellules.forEach((c, i) => {
        const a = force || tau >= 99 ? 1 : lisse(Math.min(1, Math.max(0, (tau - c.delai) / 0.45)));
        const k = cur[i];
        k.col.copy(from[i].col).lerp(to[i].col, a);
        k.h = from[i].h + (to[i].h - from[i].h) * a;
        k.mur = from[i].mur + (to[i].mur - from[i].mur) * a;
        k.trou = from[i].trou + (to[i].trou - from[i].trou) * a;
        // petit « saut » de la cellule pendant qu'elle change
        const bond = a > 0 && a < 1 ? Math.sin(a * Math.PI) * 0.035 : 0;
        m4.compose(v.set(c.x, c.y, 0), q.identity(), sc.set(1, 1, k.mur)); murs.setMatrixAt(i, m4);
        m4.compose(v.set(c.x, c.y, 0), q.identity(), sc.set(1, 1, Math.max(0.004, k.h + bond))); contenus.setMatrixAt(i, m4);
        contenus.setColorAt(i, k.col);
        const s = k.trou;
        m4.compose(v.set(c.x, c.y, k.h + bond + 0.002), q.identity(), sc.set(s, s, s)); trous.setMatrixAt(i, m4);
    });
    murs.instanceMatrix.needsUpdate = true;
    contenus.instanceMatrix.needsUpdate = true;
    contenus.instanceColor.needsUpdate = true;
    trous.instanceMatrix.needsUpdate = true;
}

/* ------------------------------------------------------------------------
   Animation des petites bêtes
   ------------------------------------------------------------------------ */
const GRIS = new THREE.Color("#9A958C"), BLANC = new THREE.Color(1, 1, 1);
const approche = (x, y, k) => x + (y - x) * k;
const bord = (b, marge) => {
    const mx = W / 2 - marge, my = H / 2 - marge;
    if (Math.abs(b.x) > mx) { b.x = Math.sign(b.x) * mx; b.h = Math.PI - b.h; }
    if (Math.abs(b.y) > my) { b.y = Math.sign(b.y) * my; b.h = -b.h; }
};

function animerBetes(dt, temps) {
    const k = 1 - Math.exp(-dt * 3);
    bees.forEach((b, i) => {
        const visible = i < cible.abeilles;
        b.vis = approche(b.vis, visible ? 1 : 0, k);
        const malade = b.rang < cible.malades;
        b.aile = approche(b.aile, malade ? 0.45 : 1, k);
        b.aileC.lerp(malade ? GRIS : BLANC, k);
        if (!reduceMotion) {
            if (b.pause > 0) b.pause -= dt;
            else {
                b.h += (Math.random() - 0.5) * dt * 4;
                const vit = malade ? b.v * 0.35 : b.v;
                b.x += Math.cos(b.h) * vit * dt; b.y += Math.sin(b.h) * vit * dt;
                if (Math.random() < dt * 0.25) b.pause = 0.6 + Math.random() * 1.6;
            }
            bord(b, 0.2);
        }
        const s = b.vis < 0.02 ? 0.0001 : b.vis;
        q.setFromAxisAngle(AXE_Z, b.h);
        m4.compose(v.set(b.x, b.y, 0.24 + (1 - b.vis) * 0.6), q, sc.set(s * 1.15, s * 1.15, s * 1.15));
        abeilles.setMatrixAt(i, m4);
        const battement = b.pause > 0 || malade ? 1 : 1 + Math.sin(temps * 40 + i) * 0.12;
        m4.compose(v.set(b.x, b.y, 0.24 + (1 - b.vis) * 0.6), q, sc.set(s * 1.15 * b.aile, s * 1.15 * b.aile * battement, s * 1.15));
        ailes.setMatrixAt(i, m4);
        ailes.setColorAt(i, b.aileC);
        const porte = visible && b.rang > 1 - cible.varroas;
        const sv = porte ? s * 1.15 : 0.0001;
        m4.compose(v.set(b.x + Math.cos(b.h) * 0.045 * 1.15, b.y + Math.sin(b.h) * 0.045 * 1.15, 0.24 + 0.075), q, sc.set(sv, sv, sv));
        varroas.setMatrixAt(i, m4);
    });
    abeilles.instanceMatrix.needsUpdate = true;
    ailes.instanceMatrix.needsUpdate = true;
    ailes.instanceColor.needsUpdate = true;
    varroas.instanceMatrix.needsUpdate = true;

    if (SLUG === "petit-coleoptere") {
        beetles.forEach((b, i) => {
            b.vis = approche(b.vis, i < cible.coleos ? 1 : 0, k);
            if (!reduceMotion) { b.h += (Math.random() - 0.5) * dt * 3; b.x += Math.cos(b.h) * 0.07 * dt; b.y += Math.sin(b.h) * 0.07 * dt; bord(b, 0.12); }
            const s = Math.max(0.0001, b.vis) * 1.3;
            q.setFromAxisAngle(AXE_Z, b.h);
            m4.compose(v.set(b.x, b.y, 0.2), q, sc.set(s, s, s));
            coleos.setMatrixAt(i, m4);
        });
        coleos.instanceMatrix.needsUpdate = true;
    }
    if (SLUG === "nosemose") {
        spots.forEach((p, i) => {
            p.vis = approche(p.vis, i < cible.taches ? 1 : 0, k);
            const s = Math.max(0.0001, p.vis * p.s);
            m4.compose(v.set(p.x, p.y, p.z), q.identity(), sc.set(s, s * 0.8, s));
            taches.setMatrixAt(i, m4);
        });
        taches.instanceMatrix.needsUpdate = true;
    }
    frelons.forEach((g, i) => {
        const u = g.userData;
        u.vis = approche(u.vis, i < cible.frelons ? 1 : 0, k);
        const t = temps + u.phase;
        g.position.set(u.cx + Math.sin(t * 0.7) * 0.35, u.cy + Math.sin(t * 1.3) * 0.18, 1.5 + Math.sin(t * 0.5) * 0.3);
        // vu de profil, il patrouille devant le cadre en guettant les butineuses
        g.rotation.set(Math.sin(t * 0.6) * 0.12, (i % 2 ? Math.PI : 0) + 0.55 + Math.sin(t * 0.4) * 0.35, Math.sin(t * 0.9) * 0.1);
        g.scale.setScalar(Math.max(0.001, u.vis) * 1.7);
        const f = reduceMotion ? 0 : Math.sin(temps * 45 + i) * 0.5;
        u.a1.rotation.x = 0.3 + f; u.a2.rotation.x = -0.3 - f;
    });
}

/* ------------------------------------------------------------------------
   Infobulle au survol d'une cellule
   ------------------------------------------------------------------------ */
const tip = document.createElement("div");
tip.className = "evo-tip";
tip.hidden = true;
viewer.appendChild(tip);
const ray = new THREE.Raycaster(), souris = new THREE.Vector2();
let survol = null;
renderer.domElement.addEventListener("pointermove", e => { survol = e; });
renderer.domElement.addEventListener("pointerleave", () => { survol = null; tip.hidden = true; });

function majInfobulle() {
    if (!survol) return;
    const r = renderer.domElement.getBoundingClientRect();
    souris.set(((survol.clientX - r.left) / r.width) * 2 - 1, -((survol.clientY - r.top) / r.height) * 2 + 1);
    ray.setFromCamera(souris, camera);
    const hit = ray.intersectObject(contenus, false)[0];
    if (!hit) { tip.hidden = true; return; }
    const e = to[hit.instanceId].etat;
    const malade = ["perce", "affaisse", "tordue", "momie", "galerie", "fermente"].includes(e);
    tip.innerHTML = `<i style="background:#${cur[hit.instanceId].col.getHexString()}"></i>${ETATS[e].label}`;
    tip.classList.toggle("is-hit", malade);
    tip.style.transform = `translate(${survol.clientX - r.left + 14}px, ${survol.clientY - r.top + 14}px)`;
    tip.hidden = false;
    survol = null;
}

/* ------------------------------------------------------------------------
   Boucle, taille, boutons
   ------------------------------------------------------------------------ */
function resize() {
    const w = holder.clientWidth, h = holder.clientHeight;
    if (!w || !h) return;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
}
new ResizeObserver(resize).observe(holder);
resize();

let vol = null;
document.getElementById("evoReset").addEventListener("click", () => {
    vol = { t: 0, p0: camera.position.clone(), c0: controls.target.clone() };
    window.BeeFlow && window.BeeFlow.sfx.play("turn");
});

const horloge = new THREE.Clock();
function frame() {
    const dt = Math.min(0.05, horloge.getDelta()), temps = horloge.elapsedTime;
    if (tau < 99) { tau += dt; majCellules(); }
    animerBetes(dt, temps);
    if (vol) {
        vol.t = Math.min(1, vol.t + dt * 1.6);
        const a = lisse(vol.t);
        camera.position.lerpVectors(vol.p0, HOME.pos, a);
        controls.target.lerpVectors(vol.c0, HOME.target, a);
        if (vol.t >= 1) vol = null;
    }
    controls.update();
    majInfobulle();
    renderer.render(scene, camera);
    requestAnimationFrame(frame);
}

document.addEventListener("evo:etat", e => appliquer(e.detail, false));
const e0 = EVO.etat;
appliquer({ semaine: e0.semaine, scenario: e0.scenario, point: EVO.sim[e0.scenario][e0.semaine] }, true);
bees.forEach((b, i) => { b.vis = i < cible.abeilles ? 1 : 0; });

(renderer.compileAsync ? renderer.compileAsync(scene, camera) : Promise.resolve()).catch(() => {}).then(() => {
    document.getElementById("evoLoading").hidden = true;
    frame();
});
