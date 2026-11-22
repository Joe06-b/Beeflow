/* ==========================================================================
   EXPLORER UNE MALADIE EN 3D — abeille anatomique (Three.js, module ES)
   - Abeille modélisée avec des formes simples (sphères, tubes, formes planes)
   - Parties cliquables : sur le modèle, sur les points dorés, ou dans la liste
   - Bascule « Saine / Atteinte » : la maladie se dessine sur le modèle
     (acariens, ailes froissées, intestin visible, larve brune, momie, coléoptères, frelon…)
   Aucune donnée enregistrée : tout vient de maladies.py via json_script.
   ========================================================================== */
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

window.B3D_OK = true;                       // le module a bien démarré (voir le filet de sécurité du template)
const DATA = JSON.parse(document.getElementById("b3dData").textContent);
const MALADIE = (window.B3D && window.B3D.maladie) || "";
const EFFETS = new Set(DATA.effets);
const sfx = n => window.BeeFlow && window.BeeFlow.sfx.play(n);
const icon = (n, c) => (window.BeeFlow ? window.BeeFlow.icon(n, c) : "");
const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

const viewer = document.getElementById("b3dViewer");
const holder = document.getElementById("b3dCanvas");
const hotLayer = document.getElementById("b3dHotspots");

/* ------------------------------------------------------------------------
   Panneau (liste des parties + informations) : affiché tout de suite,
   sans attendre la préparation de la scène 3D
   ------------------------------------------------------------------------ */
const ORDRE = ["yeux", "antennes", "ailes", "thorax", "abdomen", "pattes", "dard", "intestin", "larve"];
let selected = null, atteinte = true;
// Liste des parties dans le panneau
const partsBox = document.getElementById("b3dParts");
ORDRE.forEach(code => {
    const info = DATA.parties[code];
    const b = document.createElement("button");
    b.type = "button"; b.className = "b3d-part" + (info.atteinte ? " is-hit" : ""); b.dataset.part = code;
    b.innerHTML = `<i></i>${info.nom.replace(" (couvain)", "")}${info.atteinte ? "<em>touchée</em>" : ""}`;
    b.addEventListener("click", () => select(code));
    partsBox.appendChild(b);
});

const infoBox = document.getElementById("b3dInfo");

function renderInfo() {
    if (!selected) {
        const touchees = ORDRE.filter(c => DATA.parties[c].atteinte).map(c => DATA.parties[c].nom.toLowerCase());
        infoBox.innerHTML = `
            <p class="b3d-kicker">${icon("microbe", "ico-sm")} ${MALADIE}</p>
            <h2>Où la maladie frappe</h2>
            <p>Parties touchées : <strong>${touchees.join(", ")}</strong>.</p>
            <p class="b3d-watch">Cliquez sur un point doré de l'abeille, ou choisissez une partie dans la liste. Les points rouges sont les parties touchées.</p>`;
        return;
    }
    const p = DATA.parties[selected];
    const touche = p.atteinte && atteinte;
    infoBox.innerHTML = `
        <p class="b3d-kicker">${icon(p.atteinte ? "alert" : "eye", "ico-sm")} ${p.atteinte ? "Partie touchée par la maladie" : "Partie de l'abeille"}</p>
        <h2>${p.nom}</h2>
        <p>${p.role}</p>
        <p class="b3d-watch"><strong>À surveiller :</strong> ${p.regarder}</p>
        ${p.atteinte ? `<div class="notice ${touche ? "is-bad" : "is-good"}">${icon(touche ? "alert" : "check")}<div><strong>${touche ? "Avec la maladie" : "Abeille saine : rien d'anormal ici"}</strong>${touche ? p.atteinte : ""}</div></div>` : ""}`;
}

renderInfo();

// On laisse le navigateur afficher le panneau AVANT de préparer la 3D (plus lourde)
await new Promise(r => requestAnimationFrame(() => setTimeout(r, 0)));

/* ------------------------------------------------------------------------
   Moteur
   ------------------------------------------------------------------------ */
let renderer;
try {
    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
} catch (e) {
    document.getElementById("b3dLoading").hidden = true;
    document.getElementById("b3dFallback").hidden = false;
    throw e;
}
renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.05;
holder.appendChild(renderer.domElement);

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(38, 1, 0.05, 100);
const HOME = { pos: new THREE.Vector3(5.6, 3.4, 7.4), target: new THREE.Vector3(0.9, -0.25, -0.25) };
camera.position.copy(HOME.pos);

const controls = new OrbitControls(camera, renderer.domElement);
controls.target.copy(HOME.target);
controls.enableDamping = true;
controls.dampingFactor = 0.08;
controls.enablePan = false;
controls.minDistance = 1.4;
controls.maxDistance = 12;
controls.autoRotateSpeed = 1.2;

// Lumières chaudes (miel)
scene.add(new THREE.HemisphereLight(0xfff3d6, 0x3a2414, 1.15));
const key = new THREE.DirectionalLight(0xfff1d0, 2.1);
key.position.set(3, 5, 4);
scene.add(key);
const rim = new THREE.PointLight(0xe9b949, 18, 12);
rim.position.set(-3, 1.5, -3);
scene.add(rim);

/* ------------------------------------------------------------------------
   Matériaux
   ------------------------------------------------------------------------ */
const MAT = {
    dark: new THREE.MeshStandardMaterial({ color: 0x2b1b0f, roughness: 0.55 }),
    eye: new THREE.MeshStandardMaterial({ color: 0x0b0704, roughness: 0.08, metalness: 0.35 }),
    thorax: new THREE.MeshStandardMaterial({ color: 0x8a5a2b, roughness: 0.85 }),
    leg: new THREE.MeshStandardMaterial({ color: 0x3a2414, roughness: 0.6 }),
    pollen: new THREE.MeshStandardMaterial({ color: 0xf0a830, roughness: 0.9 }),
    wax: new THREE.MeshStandardMaterial({ color: 0xe8c271, roughness: 0.55, side: THREE.DoubleSide }),
    waxDark: new THREE.MeshStandardMaterial({ color: 0xc99236, roughness: 0.5 }),
    honey: new THREE.MeshStandardMaterial({ color: 0xe0a020, roughness: 0.2, metalness: 0.1 }),
    mite: new THREE.MeshStandardMaterial({ color: 0x7a2f17, roughness: 0.35 }),
    beetle: new THREE.MeshStandardMaterial({ color: 0x2a1a10, roughness: 0.3, metalness: 0.15 }),
};

// Rayures de l'abdomen (texture dessinée)
function stripeTexture(colors, bands) {
    const c = document.createElement("canvas");
    c.width = 16; c.height = 512;
    const g = c.getContext("2d");
    const h = 512 / bands.length;
    bands.forEach((k, i) => { g.fillStyle = colors[k]; g.fillRect(0, i * h, 16, h + 1); });
    const t = new THREE.CanvasTexture(c);
    t.colorSpace = THREE.SRGBColorSpace;
    return t;
}
// Nervures des ailes
function veinTexture() {
    const c = document.createElement("canvas");
    c.width = c.height = 256;
    const g = c.getContext("2d");
    g.fillStyle = "#fff9ed"; g.fillRect(0, 0, 256, 256);
    g.strokeStyle = "rgba(64,40,23,.55)"; g.lineWidth = 2.2;
    [[20, 128, 240, 110], [20, 128, 230, 150], [40, 128, 150, 60], [60, 128, 180, 200], [110, 100, 130, 160], [150, 75, 175, 135]]
        .forEach(([a, b, x, y]) => { g.beginPath(); g.moveTo(a, b); g.quadraticCurveTo((a + x) / 2, (b + y) / 2 - 12, x, y); g.stroke(); });
    const t = new THREE.CanvasTexture(c);
    t.colorSpace = THREE.SRGBColorSpace;
    return t;
}

/* ------------------------------------------------------------------------
   Construction d'un insecte (abeille, ou frelon avec d'autres couleurs)
   ------------------------------------------------------------------------ */
const PARTS = {};                       // code de partie → liste de meshes (pour surligner et cliquer)
function tag(mesh, part) {
    mesh.userData.part = part;
    (PARTS[part] = PARTS[part] || []).push(mesh);
    return mesh;
}
const tube = (pts, r, mat) => new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts.map(p => new THREE.Vector3(...p))), 32, r, 8, false), mat);

function wingGeometry(len, wid) {
    const s = new THREE.Shape();
    s.moveTo(0, 0);
    s.bezierCurveTo(len * 0.25, wid * 0.9, len * 0.8, wid * 0.75, len, wid * 0.1);
    s.bezierCurveTo(len * 0.95, -wid * 0.35, len * 0.4, -wid * 0.45, 0, 0);
    const geo = new THREE.ShapeGeometry(s, 24);
    // UV normalisées pour la texture des nervures
    const pos = geo.attributes.position, uv = geo.attributes.uv;
    for (let i = 0; i < pos.count; i++) uv.setXY(i, pos.getX(i) / len, (pos.getY(i) + wid * 0.5) / (wid * 1.4));
    return geo;
}

function buildInsect(opts) {
    const o = Object.assign({
        head: 0x4a2e18, thorax: MAT.thorax, bands: null, wingTint: 0xfff9ed, scale: 1, parts: true,
    }, opts);
    const T = o.parts ? tag : (m => m);
    const root = new THREE.Group();

    // Tête
    const headMat = new THREE.MeshStandardMaterial({ color: o.head, roughness: 0.55 });
    const head = T(new THREE.Mesh(new THREE.SphereGeometry(0.32, 32, 24), headMat), "yeux");
    head.scale.set(1, 1.05, 0.85); head.position.set(0, 0.05, 1.05);
    root.add(head);
    // Yeux composés + ocelles
    [-1, 1].forEach(sx => {
        const eye = T(new THREE.Mesh(new THREE.SphereGeometry(0.21, 24, 16), MAT.eye), "yeux");
        eye.scale.set(0.62, 1.15, 0.85); eye.position.set(sx * 0.28, 0.08, 1.07);
        root.add(eye);
    });
    [[-0.07, 0.33, 1.0], [0.07, 0.33, 1.0], [0, 0.36, 1.08]].forEach(p => {
        const oc = T(new THREE.Mesh(new THREE.SphereGeometry(0.03, 10, 8), MAT.eye), "yeux");
        oc.position.set(...p); root.add(oc);
    });
    // Antennes (coudées)
    [-1, 1].forEach(sx => {
        root.add(T(tube([[sx * 0.08, 0.2, 1.3], [sx * 0.16, 0.5, 1.42], [sx * 0.2, 0.62, 1.5], [sx * 0.3, 0.55, 1.88]], 0.022, MAT.dark), "antennes"));
    });
    // Pièces buccales
    const mouth = T(new THREE.Mesh(new THREE.ConeGeometry(0.05, 0.22, 10), MAT.dark), "yeux");
    mouth.position.set(0, -0.2, 1.22); mouth.rotation.x = Math.PI * 0.75; root.add(mouth);

    // Thorax (+ poils)
    const thorax = T(new THREE.Mesh(new THREE.SphereGeometry(0.45, 32, 24), o.thorax), "thorax");
    thorax.scale.set(1, 0.95, 1.05); thorax.position.set(0, 0.02, 0.42);
    root.add(thorax);
    if (o.parts) {
        const fuzz = [], n = 600;
        for (let i = 0; i < n; i++) {
            const v = new THREE.Vector3().randomDirection();
            if (v.y < -0.55) continue;
            v.multiplyScalar(0.47 + Math.random() * 0.06);
            fuzz.push(v.x, v.y * 0.95 + 0.02, v.z * 1.05 + 0.42);
        }
        const fg = new THREE.BufferGeometry();
        fg.setAttribute("position", new THREE.Float32BufferAttribute(fuzz, 3));
        root.add(T(new THREE.Points(fg, new THREE.PointsMaterial({ color: 0xb98345, size: 0.022, transparent: true, opacity: 0.8 })), "thorax"));
    }
    // Taille fine
    const waist = new THREE.Mesh(new THREE.SphereGeometry(0.12, 16, 12), MAT.dark);
    waist.position.set(0, -0.02, -0.06); root.add(waist);

    // Abdomen rayé (les pôles de la sphère sont alignés sur l'axe du corps)
    const abGeo = new THREE.SphereGeometry(0.55, 40, 28);
    abGeo.rotateX(-Math.PI / 2);
    const abMat = new THREE.MeshStandardMaterial({
        map: stripeTexture({ h: "#E9B949", d: "#2B1B0F" }, o.bands || ["d", "h", "h", "d", "h", "d", "h", "d", "d"]),
        roughness: 0.6, transparent: true,
    });
    const abdomen = T(new THREE.Mesh(abGeo, abMat), "abdomen");
    abdomen.scale.set(0.95, 0.85, 1.55);
    abdomen.position.set(0, -0.06, -0.78);
    root.add(abdomen);

    // Dard
    const sting = T(new THREE.Mesh(new THREE.ConeGeometry(0.045, 0.24, 10), MAT.dark), "dard");
    sting.rotation.x = -Math.PI / 2; sting.position.set(0, -0.08, -1.66); root.add(sting);

    // Ailes (2 paires) sur des pivots, pour pouvoir les faire battre
    const wingMat = new THREE.MeshStandardMaterial({
        color: o.wingTint, map: o.parts ? veinTexture() : null, transparent: true, opacity: 0.45,
        roughness: 0.15, metalness: 0.2, side: THREE.DoubleSide, depthWrite: false,
    });
    const wings = [];
    [-1, 1].forEach(sx => {
        [[1.3, 0.45, 0.62, 0.42], [0.9, 0.32, 0.38, 0.4]].forEach(([len, wid, z, y], k) => {
            const pivot = new THREE.Group();
            pivot.position.set(sx * 0.18, y, z);
            const geo = wingGeometry(len, wid);
            const w = T(new THREE.Mesh(geo, wingMat), "ailes");
            w.rotation.set(-Math.PI / 2 + 0.12, 0, 0);       // à plat sur le dos
            w.scale.x = sx;                                    // symétrie gauche / droite
            pivot.add(w);
            pivot.rotation.y = sx * (k ? 0.61 : 0.87);         // repliées vers l'arrière (40° et 55° de l'axe)
            pivot.rotation.z = sx * 0.1;
            pivot.userData = { sx, base: pivot.rotation.clone() };
            root.add(pivot);
            wings.push({ pivot, mesh: w, geo, orig: Float32Array.from(geo.attributes.position.array) });
        });
    });

    // Pattes : 3 paires, la dernière avec une pelote de pollen
    [[0.62, 1.0], [0.42, 1.1], [0.2, 1.3]].forEach(([z, l], k) => {
        [-1, 1].forEach(sx => {
            const pts = [[sx * 0.2, -0.28, z], [sx * 0.55, -0.35, z + 0.08 * (1 - k)], [sx * 0.72 * l, -0.7, z - 0.15 * k], [sx * 0.82 * l, -1.0, z - 0.3 * k]];
            root.add(T(tube(pts, 0.028, MAT.leg), "pattes"));
            if (k === 2 && o.parts) {
                const p = T(new THREE.Mesh(new THREE.SphereGeometry(0.1, 16, 12), MAT.pollen), "pattes");
                p.scale.set(0.8, 1.1, 1); p.position.set(sx * 0.74 * l, -0.76, z - 0.18 * k); root.add(p);
            }
        });
    });

    root.scale.setScalar(o.scale);
    return { root, abdomen, abMat, thorax, wings, head };
}

/* ------------------------------------------------------------------------
   La scène : abeille + alvéole avec larve + ombre au sol
   ------------------------------------------------------------------------ */
const bee = buildInsect({});
scene.add(bee.root);

// Ombre douce au sol (texture radiale)
(function ground() {
    const c = document.createElement("canvas"); c.width = c.height = 128;
    const g = c.getContext("2d"), gr = g.createRadialGradient(64, 64, 4, 64, 64, 64);
    gr.addColorStop(0, "rgba(0,0,0,.55)"); gr.addColorStop(1, "rgba(0,0,0,0)");
    g.fillStyle = gr; g.fillRect(0, 0, 128, 128);
    const m = new THREE.Mesh(new THREE.PlaneGeometry(4.2, 4.2), new THREE.MeshBasicMaterial({ map: new THREE.CanvasTexture(c), transparent: true, depthWrite: false }));
    m.rotation.x = -Math.PI / 2; m.position.set(0, -1.05, -0.1); scene.add(m);
})();

// Intestin (caché dans l'abdomen ; visible pour la nosémose ou quand on clique dessus)
const gutMat = new THREE.MeshStandardMaterial({ color: 0xd99a5a, roughness: 0.5, emissive: 0x000000 });
const gut = tag(tube([[0, -0.02, -0.12], [0.12, 0, -0.45], [-0.15, -0.05, -0.75], [0.15, -0.1, -1.0], [-0.08, -0.1, -1.25], [0, -0.08, -1.5]], 0.09, gutMat), "intestin");
gut.visible = false;
scene.add(gut);
const spores = (() => {
    const pts = [];
    for (let i = 0; i < 160; i++) {
        const t = Math.random(), p = gut.geometry.parameters.path.getPointAt(t);
        pts.push(p.x + (Math.random() - .5) * .16, p.y + (Math.random() - .5) * .16, p.z + (Math.random() - .5) * .16);
    }
    const g = new THREE.BufferGeometry(); g.setAttribute("position", new THREE.Float32BufferAttribute(pts, 3));
    const s = new THREE.Points(g, new THREE.PointsMaterial({ color: 0xffffff, size: 0.04, transparent: true, opacity: 0 }));
    scene.add(s); return s;
})();

// Morceau de rayon avec l'alvéole de la larve (à droite de l'abeille)
const comb = new THREE.Group();
comb.position.set(2.35, -0.72, -0.5);
scene.add(comb);
const CELL_R = 0.42, CELL_H = 0.36;
function cell(x, z, capped) {
    const g = new THREE.Group();
    const wall = new THREE.Mesh(new THREE.CylinderGeometry(CELL_R, CELL_R, CELL_H, 6, 1, true), MAT.wax);
    wall.rotation.y = Math.PI / 6; g.add(wall);
    const bottom = new THREE.Mesh(new THREE.CircleGeometry(CELL_R, 6), MAT.waxDark);
    bottom.rotation.x = -Math.PI / 2; bottom.rotation.z = Math.PI / 6; bottom.position.y = -CELL_H / 2 + 0.01; g.add(bottom);
    if (capped) {
        const cap = new THREE.Mesh(new THREE.CircleGeometry(CELL_R * 0.98, 6), capped === "miel" ? MAT.honey : MAT.waxDark);
        cap.rotation.x = -Math.PI / 2; cap.rotation.z = Math.PI / 6; cap.position.y = CELL_H / 2 - 0.02; g.add(cap);
    }
    g.position.set(x, 0, z);
    comb.add(g);
    return g;
}
const W = Math.sqrt(3) * CELL_R;
const mainCell = cell(0, 0, false);
[[W, 0, "miel"], [-W, 0, "couvain"], [W / 2, 1.5 * CELL_R, "miel"], [-W / 2, 1.5 * CELL_R, "couvain"], [W / 2, -1.5 * CELL_R, "couvain"], [-W / 2, -1.5 * CELL_R, "miel"]]
    .forEach(([x, z, c]) => cell(x, z, c));

// Larve en forme de C
const larvaMat = new THREE.MeshStandardMaterial({ color: 0xfbf3e0, roughness: 0.35 });
const larva = tag(new THREE.Mesh(new THREE.TorusGeometry(0.2, 0.095, 16, 40, Math.PI * 1.7), larvaMat), "larve");
larva.rotation.x = -Math.PI / 2;
larva.position.set(0, -CELL_H / 2 + 0.1, 0);
mainCell.add(larva);
// Opercule percé (loque américaine)
const sunkenCap = new THREE.Mesh(new THREE.SphereGeometry(CELL_R * 1.4, 24, 8, 0, Math.PI * 2, 0, 0.55),
    new THREE.MeshStandardMaterial({ color: 0x8a5a2b, roughness: 0.8, side: THREE.DoubleSide, transparent: true, opacity: 0 }));
sunkenCap.rotation.x = Math.PI; sunkenCap.position.y = CELL_H / 2 + 0.42; sunkenCap.scale.set(0.72, 0.5, 0.72);
mainCell.add(sunkenCap);
const hole = new THREE.Mesh(new THREE.CircleGeometry(0.06, 12), new THREE.MeshBasicMaterial({ color: 0x120a04, transparent: true, opacity: 0 }));
hole.rotation.x = -Math.PI / 2; hole.position.set(0.08, CELL_H / 2 - 0.04, 0.05); mainCell.add(hole);

/* ------------------------------------------------------------------------
   Éléments qui n'apparaissent que si l'abeille est atteinte
   ------------------------------------------------------------------------ */
const extras = [];                       // { obj, show: (t) => scale }
function mite(parent, pos, rot, s) {
    const g = new THREE.Group();
    const body = new THREE.Mesh(new THREE.SphereGeometry(0.075, 16, 12), MAT.mite);
    body.scale.set(1.35, 0.5, 1); g.add(body);
    for (let i = 0; i < 4; i++) [-1, 1].forEach(sx => {
        const leg = new THREE.Mesh(new THREE.CylinderGeometry(0.006, 0.006, 0.07, 4), MAT.mite);
        leg.position.set(-0.06 + i * 0.03, -0.01, sx * 0.07); leg.rotation.x = sx * 1.1; g.add(leg);
    });
    g.position.copy(pos); g.lookAt(pos.clone().multiplyScalar(2)); g.rotateX(Math.PI / 2); g.rotateY(rot);
    g.userData.s = s || 1; g.scale.setScalar(0.0001);
    parent.add(g); extras.push(g);
    return g;
}
if (EFFETS.has("acariens")) {
    [[0.42, 0.2, -0.55, 0.3], [-0.35, 0.3, -0.95, 1.2], [0.3, -0.25, -1.15, 2], [0.05, 0.46, 0.3, 0.6], [-0.4, -0.1, -0.4, 1.5]]
        .forEach(([x, y, z, r], i) => mite(scene, new THREE.Vector3(x, y, z), r, i === 3 ? 1.1 : 1));
}
if (EFFETS.has("larve_acariens")) {
    [[0.18, -0.08, 0.1, 0], [-0.15, -0.1, -0.12, 2]].forEach(([x, y, z, r]) => {
        const m = mite(mainCell, new THREE.Vector3(x, y, z), r, 0.9);
        m.position.set(x, y, z);
    });
}
if (EFFETS.has("coleopteres")) {
    [[0.15, CELL_H / 2 + 0.06, 0.25, 0.4], [-W * 0.9, CELL_H / 2 + 0.06, 0.4, 2.1], [W * 0.6, CELL_H / 2 + 0.06, -0.5, 4]].forEach(([x, y, z, r]) => {
        const g = new THREE.Group();
        const body = new THREE.Mesh(new THREE.SphereGeometry(0.11, 18, 12), MAT.beetle); body.scale.set(0.75, 0.45, 1.15); g.add(body);
        const headB = new THREE.Mesh(new THREE.SphereGeometry(0.06, 12, 10), MAT.beetle); headB.position.z = 0.14; g.add(headB);
        [-1, 1].forEach(sx => {
            const a = new THREE.Mesh(new THREE.CylinderGeometry(0.006, 0.006, 0.09, 4), MAT.beetle);
            a.position.set(sx * 0.03, 0.02, 0.21); a.rotation.x = 1.2; a.rotation.z = sx * 0.5; g.add(a);
        });
        g.position.set(x, y, z); g.rotation.y = r; g.userData.s = 1; g.scale.setScalar(0.0001);
        comb.add(g); extras.push(g);
    });
}
let hornet = null;
if (EFFETS.has("frelon")) {
    hornet = buildInsect({ head: 0xd9902a, thorax: new THREE.MeshStandardMaterial({ color: 0x1e140c, roughness: 0.6 }), bands: ["d", "d", "d", "d", "d", "d", "h", "d", "d"], wingTint: 0xbfa98a, parts: false, scale: 0.0001 });
    hornet.root.position.set(-2.6, 1.3, -2.2);
    hornet.root.rotation.y = 0.9;
    hornet.root.userData.s = 1.1;
    scene.add(hornet.root);
}
let targetRing = null;
if (EFFETS.has("thorax_cible")) {
    targetRing = new THREE.Mesh(new THREE.TorusGeometry(0.62, 0.018, 8, 64), new THREE.MeshBasicMaterial({ color: 0xe0574a, transparent: true, opacity: 0 }));
    targetRing.position.copy(bee.thorax.position); targetRing.rotation.x = Math.PI / 2;
    scene.add(targetRing);
}

// Ailes froissées : on prépare une version déformée de chaque aile
const crumple = EFFETS.has("ailes_froissees");
bee.wings.forEach((w, i) => {
    const a = w.orig, out = new Float32Array(a.length);
    for (let k = 0; k < a.length; k += 3) {
        const x = a[k], y = a[k + 1];
        out[k] = x * 0.55 + Math.sin(y * 18 + i) * 0.03;
        out[k + 1] = y * 0.75 + Math.sin(x * 14) * 0.04;
        out[k + 2] = Math.sin(x * 11 + i) * 0.07 + Math.cos(y * 16) * 0.05;
    }
    w.crumpled = out;
});

/* ------------------------------------------------------------------------
   Points cliquables (positions dans l'espace, projetées à l'écran)
   ------------------------------------------------------------------------ */
const ANCRES = {
    yeux: [0.42, 0.14, 1.1], antennes: [0.3, 0.6, 1.75], ailes: [1.15, 0.55, -0.35], thorax: [0, 0.5, 0.45],
    abdomen: [0, 0.42, -0.85], pattes: [0.8, -0.78, 0.25], dard: [0, -0.08, -1.8], intestin: [-0.55, -0.1, -0.8],
    larve: [2.35, -0.55, -0.5],
};
const VUES = {      // [position caméra, cible]
    yeux: [[3.0, 1.0, 3.6], [0.1, 0.05, 1.0]], antennes: [[2.8, 1.8, 4.0], [0.15, 0.4, 1.3]],
    ailes: [[2.6, 4.6, -0.4], [0.4, 0.3, -0.3]], thorax: [[3.0, 2.0, 2.6], [0, 0.05, 0.3]],
    abdomen: [[3.6, 1.8, -1.9], [0, -0.06, -0.75]], pattes: [[3.4, -0.3, 3.0], [0.4, -0.55, 0.2]],
    dard: [[2.2, 0.9, -4.0], [0, -0.08, -1.4]], intestin: [[3.8, 1.3, -1.4], [0, -0.06, -0.75]],
    larve: [[3.1, 2.5, 0.6], [2.35, -0.8, -0.5]],
};
const hotspots = {};
ORDRE.forEach(code => {
    const info = DATA.parties[code];
    const b = document.createElement("button");
    b.type = "button";
    b.className = "b3d-hot" + (info.atteinte ? " is-hit" : "");
    b.innerHTML = `<span>${info.nom}</span>`;
    b.setAttribute("aria-label", info.nom + (info.atteinte ? " (partie touchée)" : ""));
    b.addEventListener("click", () => select(code));
    hotLayer.appendChild(b);
    hotspots[code] = { el: b, pos: new THREE.Vector3(...ANCRES[code]) };
});

/* ------------------------------------------------------------------------
   Caméra : déplacement en douceur vers une partie
   ------------------------------------------------------------------------ */
let tween = null;
function flyTo(pos, target, ms) {
    tween = { p0: camera.position.clone(), t0: controls.target.clone(), p1: new THREE.Vector3(...pos), t1: new THREE.Vector3(...target), start: performance.now(), ms: reduceMotion ? 1 : (ms || 1000) };
}

function select(code, silencieux) {
    selected = code;
    if (!silencieux) sfx("select");
    Object.entries(hotspots).forEach(([c, h]) => h.el.classList.toggle("is-selected", c === code));
    partsBox.querySelectorAll(".b3d-part").forEach(b => b.classList.toggle("is-selected", b.dataset.part === code));
    const v = VUES[code];
    if (v) flyTo(v[0], v[1]);
    setSpin(false);
    renderInfo();
}

/* ------------------------------------------------------------------------
   Clic directement sur le modèle (raycast), sans gêner la rotation
   ------------------------------------------------------------------------ */
const ray = new THREE.Raycaster(), ndc = new THREE.Vector2();
let downAt = null;
renderer.domElement.addEventListener("pointerdown", e => { downAt = [e.clientX, e.clientY]; });
renderer.domElement.addEventListener("pointerup", e => {
    if (!downAt || Math.hypot(e.clientX - downAt[0], e.clientY - downAt[1]) > 5) return;
    const r = renderer.domElement.getBoundingClientRect();
    ndc.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
    ray.setFromCamera(ndc, camera);
    const cibles = Object.values(PARTS).flat().filter(o => o.visible && o.isMesh);
    const hit = ray.intersectObjects(cibles, false)[0];
    if (hit) select(hit.object.userData.part);
});

/* ------------------------------------------------------------------------
   Bascule Saine / Atteinte
   ------------------------------------------------------------------------ */
let tState = 1;                 // 0 = saine, 1 = atteinte (valeur animée)
document.querySelectorAll(".b3d-switch [data-etat]").forEach(btn => btn.addEventListener("click", () => {
    atteinte = btn.dataset.etat === "atteinte";
    document.querySelectorAll(".b3d-switch [data-etat]").forEach(b => {
        const on = b === btn; b.classList.toggle("is-active", on); b.setAttribute("aria-pressed", on);
    });
    Object.entries(hotspots).forEach(([c, h]) => h.el.classList.toggle("is-hit", atteinte && !!DATA.parties[c].atteinte));
    sfx(atteinte ? "regleKo" : "regleOk");
    renderInfo();
}));

/* ------------------------------------------------------------------------
   Outils
   ------------------------------------------------------------------------ */
const spinBtn = document.getElementById("b3dSpin"), flyBtn = document.getElementById("b3dFly");
function setSpin(on) { controls.autoRotate = on; spinBtn.setAttribute("aria-pressed", on); }
spinBtn.addEventListener("click", () => { setSpin(!controls.autoRotate); sfx("select"); });
let flying = false;
flyBtn.addEventListener("click", () => { flying = !flying; flyBtn.setAttribute("aria-pressed", flying); sfx("select"); });
document.getElementById("b3dReset").addEventListener("click", () => {
    selected = null; renderInfo();
    Object.values(hotspots).forEach(h => h.el.classList.remove("is-selected"));
    partsBox.querySelectorAll(".b3d-part").forEach(b => b.classList.remove("is-selected"));
    flyTo(HOME.pos.toArray(), HOME.target.toArray()); sfx("turn");
});
document.querySelector(".tabs .is-disabled")?.addEventListener("click", e => {
    e.preventDefault();
    window.BeeFlow && BeeFlow.toast("La vue <strong>Évolution dans la ruche</strong> arrive à la prochaine étape.", "info");
});

/* ------------------------------------------------------------------------
   Taille
   ------------------------------------------------------------------------ */
function resize() {
    const w = viewer.clientWidth, h = viewer.clientHeight;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
}
new ResizeObserver(resize).observe(viewer);
resize();

/* ------------------------------------------------------------------------
   Boucle d'animation : effets de la maladie, battement d'ailes, points
   ------------------------------------------------------------------------ */
const ease = t => t < .5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
const lerp = (a, b, t) => a + (b - a) * t;
const tmp = new THREE.Vector3(), camDir = new THREE.Vector3(), center = new THREE.Vector3(0.5, -0.2, -0.2);
const colLarve = { saine: new THREE.Color(0xfbf3e0), brune: new THREE.Color(0x6e4019), tordue: new THREE.Color(0xc99a40), momie: new THREE.Color(0xf2f0ea) };
const red = new THREE.Color(0xe0574a), honeyGlow = new THREE.Color(0xe9b949);
const clock = new THREE.Clock();

function applyEffects(t, time) {
    // t : 0 → abeille saine, 1 → abeille atteinte
    const pulse = 0.5 + 0.5 * Math.sin(time * 4);

    // La partie choisie s'éclaire légèrement (lueur miel, ou rouge si elle est touchée)
    // Les couleurs naturelles restent : les parties touchées sont signalées par les points rouges et les effets.
    Object.entries(PARTS).forEach(([code, meshes]) => {
        const sel = code === selected;
        const hit = !!DATA.parties[code]?.atteinte && t > 0.5;
        meshes.forEach(m => {
            if (!m.material || !m.material.emissive) return;
            // matériau partagé entre plusieurs parties → copie, pour n'éclairer que cette partie
            if (!m.userData.mat && Object.values(MAT).includes(m.material)) m.material = m.material.clone();
            m.userData.mat = true;
            m.material.emissive.copy(hit ? red : honeyGlow);
            m.material.emissiveIntensity = sel ? (hit ? 0.1 + 0.1 * pulse : 0.07) : 0;
        });
    });

    // Acariens, coléoptères, frelon : apparition progressive
    extras.forEach(o => o.scale.setScalar(Math.max(0.0001, ease(t) * o.userData.s)));
    if (hornet) {
        hornet.root.scale.setScalar(Math.max(0.0001, ease(t) * hornet.root.userData.s));
        hornet.root.position.y = 1.3 + Math.sin(time * 2.2) * 0.08;
        hornet.wings.forEach(w => { w.pivot.rotation.z = w.pivot.userData.base.z + Math.sin(time * 40) * 0.35 * w.pivot.userData.sx; });
    }
    if (targetRing) { targetRing.material.opacity = t * (0.4 + 0.5 * pulse); targetRing.scale.setScalar(1 + pulse * 0.08); }

    // Abdomen : gonflé (nosémose) ou raccourci (ailes déformées)
    let sx = 0.95, sz = 1.55;
    if (EFFETS.has("abdomen_gonfle")) { sx = lerp(0.95, 1.08, t); sz = lerp(1.55, 1.65, t); }
    if (EFFETS.has("abdomen_court")) { sz = lerp(1.55, 1.18, t); bee.abdomen.position.z = lerp(-0.78, -0.62, t); }
    bee.abdomen.scale.set(sx, lerp(0.85, 0.85 * (sx / 0.95), 1), sz);

    // Intestin : visible pour la nosémose, ou quand on choisit « Intestin »
    const showGut = EFFETS.has("intestin") ? Math.max(t, selected === "intestin" ? 1 : 0) : (selected === "intestin" ? 1 : 0);
    gut.visible = showGut > 0.02;
    bee.abMat.opacity = lerp(1, 0.28, showGut);
    bee.abMat.depthWrite = showGut < 0.5;
    const sick = EFFETS.has("intestin") ? t : 0;
    gutMat.color.setRGB(lerp(0.85, 0.75, sick), lerp(0.6, 0.27, sick), lerp(0.35, 0.2, sick));
    spores.material.opacity = sick * showGut;

    // Ailes froissées
    if (crumple) bee.wings.forEach(w => {
        const a = w.geo.attributes.position.array, k = ease(t);
        for (let i = 0; i < a.length; i++) a[i] = lerp(w.orig[i], w.crumpled[i], k);
        w.geo.attributes.position.needsUpdate = true;
    });

    // Larve
    const L = ease(t);
    larva.rotation.set(-Math.PI / 2, 0, 0); larva.scale.set(1, 1, 1);
    if (EFFETS.has("larve_fondue")) {
        larvaMat.color.copy(colLarve.saine).lerp(colLarve.brune, L);
        larvaMat.roughness = lerp(0.35, 0.1, L);
        larva.scale.set(lerp(1, 1.15, L), lerp(1, 1.15, L), lerp(1, 0.35, L));
        sunkenCap.material.opacity = L; hole.material.opacity = L;
    } else if (EFFETS.has("larve_tordue")) {
        larvaMat.color.copy(colLarve.saine).lerp(colLarve.tordue, L);
        larva.rotation.set(-Math.PI / 2 + L * 0.7, L * 0.5, L * 0.6);
    } else if (EFFETS.has("larve_momie")) {
        larvaMat.color.copy(colLarve.saine).lerp(colLarve.momie, L);
        larvaMat.roughness = lerp(0.35, 1, L);
        larva.scale.setScalar(lerp(1, 0.82, L));
    } else {
        larvaMat.color.copy(colLarve.saine);
    }

    // Battement d'ailes (ralenti pour qu'on le voie)
    bee.wings.forEach(w => {
        const base = w.pivot.userData.base;
        const amp = flying && !(crumple && t > 0.5) ? 0.55 : 0.03;
        w.pivot.rotation.z = base.z + Math.sin(time * (flying ? 22 : 2)) * amp * w.pivot.userData.sx;
    });
    bee.root.position.y = flying ? Math.sin(time * 3) * 0.06 + 0.08 : 0;
}

function placeHotspots() {
    const w = viewer.clientWidth, h = viewer.clientHeight;
    camDir.copy(camera.position).sub(center).normalize();
    Object.entries(hotspots).forEach(([code, hs]) => {
        tmp.copy(hs.pos);
        const facing = tmp.clone().sub(center).normalize().dot(camDir);
        tmp.project(camera);
        const visible = tmp.z < 1;
        hs.el.hidden = !visible;
        hs.el.style.transform = `translate(${(tmp.x * 0.5 + 0.5) * w}px, ${(-tmp.y * 0.5 + 0.5) * h}px) translate(-9px, -50%)`;
        hs.el.classList.toggle("is-behind", facing < -0.35 && code !== selected);
    });
}

function frame() {
    const time = clock.getElapsedTime();
    // état animé saine ↔ atteinte
    tState += ((atteinte ? 1 : 0) - tState) * 0.08;
    if (tween) {
        const k = Math.min(1, (performance.now() - tween.start) / tween.ms), e = ease(k);
        camera.position.lerpVectors(tween.p0, tween.p1, e);
        controls.target.lerpVectors(tween.t0, tween.t1, e);
        if (k >= 1) tween = null;
    }
    controls.update();
    applyEffects(tState, time);
    renderer.render(scene, camera);
    placeHotspots();
    requestAnimationFrame(frame);
}

/* ------------------------------------------------------------------------
   Démarrage : on montre d'abord la partie la plus touchée
   ------------------------------------------------------------------------ */
tState = 0;                               // l'abeille commence saine puis la maladie apparaît
const demarrer = () => {
    document.getElementById("b3dLoading").hidden = true;
    frame();
    setTimeout(() => { if (!selected) select(DATA.focus, true); }, reduceMotion ? 0 : 900);
};
// compileAsync prépare les shaders sans bloquer la page (sinon Windows peut figer plusieurs secondes)
(renderer.compileAsync ? renderer.compileAsync(scene, camera) : Promise.resolve()).catch(() => {}).then(demarrer);
