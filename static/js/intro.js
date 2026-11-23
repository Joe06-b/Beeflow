/* ==========================================================================
   BEEFLOW — INTRO « L'ABEILLE QUI DESSINE »
   Après le clic sur « Entrer dans BeeFlow » :
     0.0 s  l'abeille s'envole du bouton
     0.7 s  elle trace l'hexagone du logo avec une traînée de miel (bruit de crayon)
     2.5 s  elle écrit « BeeFlow » : le mot apparaît derrière elle
     4.3 s  l'alvéole se remplit de miel (versement), le logo apparaît (petite mélodie)
     5.9 s  on plonge dans l'alvéole : elle s'agrandit et devient la page d'accueil (souffle)
     7.0 s  l'abeille se pose sur « Accéder à mon espace », puis repart
   Tous les sons sont générés par la Web Audio API (aucun fichier audio).
   ========================================================================== */
(function () {
    "use strict";

    const intro = document.getElementById("intro");
    const beeEl = document.getElementById("introBee");
    if (!intro || !beeEl) return;

    const canvas = document.getElementById("introCanvas");
    const ctx = canvas.getContext("2d");
    const word = document.getElementById("introWord");
    const tagline = document.getElementById("introTagline");
    const start = document.getElementById("introStart");
    const btnEnter = document.getElementById("introEnter");
    const btnSkip = document.getElementById("introSkip");
    const btnSound = document.getElementById("introSound");
    const ICONS = document.body.dataset.icons || "/static/img/icons.svg";

    const C = { propolis: "#2B1B0F", honey: "#E9B949", honey2: "#F4D27E", deep: "#C9921A", wax: "#FFF9ED" };
    const T = { takeoff: 0, draw: 700, toWord: 2500, write: 3000, fill: 4300, dive: 5900, land: 7000, leave: 8300, end: 9100 };

    const logo = new Image();
    logo.src = (document.querySelector('link[rel="icon"]') || {}).href || "/static/img/logo.svg";

    let W = 0, H = 0, dpr = 1;
    let G = {};                         // géométrie (hexagone, mot, bouton)
    let phase = "idle", tStart = 0, rafId = 0;
    let bee = { x: 0, y: 0, rot: 0, scale: 1 };
    let sparks = [];
    let soundOn = true;
    try { soundOn = localStorage.getItem("beeflow_son") !== "0"; } catch (e) {}

    /* ------------------------------------------------------------------
       Géométrie
       ------------------------------------------------------------------ */
    function layout() {
        dpr = Math.min(window.devicePixelRatio || 1, 2);
        W = window.innerWidth; H = window.innerHeight;
        canvas.width = W * dpr; canvas.height = H * dpr;
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

        const R = Math.max(58, Math.min(118, Math.min(W, H) * 0.15));
        const cx = W / 2, cy = H * 0.38;
        const v = [];
        for (let i = 0; i < 6; i++) {
            const a = Math.PI / 180 * (60 * i - 90);
            v.push({ x: cx + R * Math.cos(a), y: cy + R * Math.sin(a) });
        }
        const wordTop = cy + R + 38;
        word.style.top = wordTop + "px";
        const wr = word.getBoundingClientRect();
        tagline.style.top = (wordTop + wr.height + 16) + "px";
        start.style.top = (wordTop + 8) + "px";

        // grille d'alvéoles du fond
        const cells = [], r = 30, cw = Math.sqrt(3) * r, ch = 1.5 * r;
        for (let row = -1, y = 0; y < H + r * 2; row++, y = row * ch) {
            for (let x = -cw + ((row & 1) ? cw / 2 : 0); x < W + cw; x += cw) cells.push({ x, y });
        }
        G = { R, cx, cy, v, cells, word: { left: wr.left, right: wr.right, top: wr.top, h: wr.height } };
    }

    function hexPath(c, x, y, r) {
        c.moveTo(x + r * Math.cos(-Math.PI / 2), y + r * Math.sin(-Math.PI / 2));
        for (let i = 1; i < 6; i++) {
            const a = Math.PI / 180 * (60 * i - 90);
            c.lineTo(x + r * Math.cos(a), y + r * Math.sin(a));
        }
        c.closePath();
    }

    // point sur le périmètre de l'hexagone, u ∈ [0, 1]
    function perimeter(u) {
        const e = Math.min(5.9999, u * 6), i = Math.floor(e), k = e - i;
        const a = G.v[i], b = G.v[(i + 1) % 6];
        return { x: a.x + (b.x - a.x) * k, y: a.y + (b.y - a.y) * k };
    }

    const ease = t => t < .5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
    const clamp01 = t => Math.max(0, Math.min(1, t));
    const lerp = (a, b, t) => a + (b - a) * t;
    function bezier(p0, p1, p2, t) {
        const u = 1 - t;
        return { x: u * u * p0.x + 2 * u * t * p1.x + t * t * p2.x, y: u * u * p0.y + 2 * u * t * p1.y + t * t * p2.y };
    }
    function ctaPoint() {
        const cta = document.querySelector(".hero-cta .btn-honey");
        if (!cta) return { x: W * 0.25, y: H * 0.6 };
        const r = cta.getBoundingClientRect();
        return { x: r.right - 18, y: r.top - 14 };
    }

    /* ------------------------------------------------------------------
       Son (Web Audio API)
       ------------------------------------------------------------------ */
    let A = null, buzz = null, scratch = null;

    function noiseBuffer(sec) {
        const b = A.createBuffer(1, Math.floor(A.sampleRate * sec), A.sampleRate), d = b.getChannelData(0);
        for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
        return b;
    }

    function audioInit() {
        if (!soundOn || A) return;
        try {
            A = new (window.AudioContext || window.webkitAudioContext)();

            // Bourdonnement d'UNE abeille : doux, il suit la vitesse et la position (gauche/droite)
            const o1 = A.createOscillator(), o2 = A.createOscillator();
            o1.type = o2.type = "sawtooth"; o1.frequency.value = 228; o2.frequency.value = 232;
            const bp = A.createBiquadFilter(); bp.type = "bandpass"; bp.frequency.value = 620; bp.Q.value = 1.4;
            const trem = A.createGain(); trem.gain.value = .7;
            const lfo = A.createOscillator(); lfo.frequency.value = 34;
            const lfoG = A.createGain(); lfoG.gain.value = .3; lfo.connect(lfoG).connect(trem.gain);
            const pan = A.createStereoPanner ? A.createStereoPanner() : A.createGain();
            const vol = A.createGain(); vol.gain.value = 0.0001;
            o1.connect(bp); o2.connect(bp); bp.connect(trem).connect(pan).connect(vol).connect(A.destination);
            o1.start(); o2.start(); lfo.start();
            buzz = { o1, o2, pan, vol };

            // Bruit de crayon (bruit blanc filtré, volume piloté pendant le tracé)
            const src = A.createBufferSource(); src.buffer = noiseBuffer(2); src.loop = true;
            const hp = A.createBiquadFilter(); hp.type = "highpass"; hp.frequency.value = 1800;
            const bp2 = A.createBiquadFilter(); bp2.type = "bandpass"; bp2.frequency.value = 3600; bp2.Q.value = .6;
            const sv = A.createGain(); sv.gain.value = 0;
            src.connect(hp).connect(bp2).connect(sv).connect(A.destination); src.start();
            scratch = { vol: sv };

            buzz.vol.gain.setTargetAtTime(0.05, A.currentTime, 0.15);
        } catch (e) { A = null; }
    }

    function audioBee(speed, x, resting) {
        if (!A || !buzz) return;
        const t = A.currentTime;
        const f = 210 + Math.min(80, speed * 9);
        buzz.o1.frequency.setTargetAtTime(f, t, 0.08);
        buzz.o2.frequency.setTargetAtTime(f + 4, t, 0.08);
        if (buzz.pan.pan) buzz.pan.pan.setTargetAtTime((x / W * 2 - 1) * 0.7, t, 0.1);
        buzz.vol.gain.setTargetAtTime(resting ? 0.012 : 0.05, t, 0.2);
    }

    function audioScratch(on) {
        if (!A || !scratch) return;
        scratch.vol.gain.setTargetAtTime(on ? 0.035 + Math.random() * 0.03 : 0, A.currentTime, 0.03);
    }

    function audioPour() {
        if (!A) return;
        const t = A.currentTime, src = A.createBufferSource(); src.buffer = noiseBuffer(1.4);
        const lp = A.createBiquadFilter(); lp.type = "lowpass"; lp.Q.value = 4;
        lp.frequency.setValueAtTime(260, t); lp.frequency.exponentialRampToValueAtTime(1500, t + 1.2);
        const g = A.createGain(); g.gain.setValueAtTime(0.0001, t);
        g.gain.exponentialRampToValueAtTime(0.07, t + 0.2); g.gain.exponentialRampToValueAtTime(0.0001, t + 1.35);
        src.connect(lp).connect(g).connect(A.destination); src.start(t);
    }

    function audioChime() {                       // do – mi – sol – do : petite mélodie claire
        if (!A) return;
        [523.25, 659.25, 783.99, 1046.5].forEach((f, i) => {
            const t = A.currentTime + i * 0.14;
            [[f, "sine", 0.13], [f * 2, "triangle", 0.03]].forEach(([fr, type, v]) => {
                const o = A.createOscillator(), g = A.createGain();
                o.type = type; o.frequency.value = fr;
                g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(v, t + 0.01);
                g.gain.exponentialRampToValueAtTime(0.0001, t + 1.3);
                o.connect(g).connect(A.destination); o.start(t); o.stop(t + 1.4);
            });
        });
    }

    function audioWhoosh() {
        if (!A) return;
        const t = A.currentTime, src = A.createBufferSource(); src.buffer = noiseBuffer(1.1);
        const bp = A.createBiquadFilter(); bp.type = "bandpass"; bp.Q.value = .9;
        bp.frequency.setValueAtTime(280, t); bp.frequency.exponentialRampToValueAtTime(2600, t + 0.9);
        const g = A.createGain(); g.gain.setValueAtTime(0.0001, t);
        g.gain.exponentialRampToValueAtTime(0.18, t + 0.35); g.gain.exponentialRampToValueAtTime(0.0001, t + 1.05);
        src.connect(bp).connect(g).connect(A.destination); src.start(t);
    }

    function audioBlip() {                        // l'abeille se pose
        if (!A) return;
        const t = A.currentTime, o = A.createOscillator(), g = A.createGain();
        o.type = "sine"; o.frequency.setValueAtTime(880, t); o.frequency.exponentialRampToValueAtTime(1320, t + 0.08);
        g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(0.09, t + 0.01); g.gain.exponentialRampToValueAtTime(0.0001, t + 0.22);
        o.connect(g).connect(A.destination); o.start(t); o.stop(t + 0.25);
    }

    function audioStop(after) {
        if (!A) return;
        const ctxA = A; A = null;
        try {
            buzz.vol.gain.setTargetAtTime(0, ctxA.currentTime, 0.2);
            scratch.vol.gain.setTargetAtTime(0, ctxA.currentTime, 0.05);
        } catch (e) {}
        setTimeout(() => { try { ctxA.close(); } catch (e) {} }, (after || 600));
    }

    function setSound(on) {
        soundOn = on;
        try { localStorage.setItem("beeflow_son", on ? "1" : "0"); } catch (e) {}
        btnSound.setAttribute("aria-pressed", on);
        btnSound.innerHTML = `<svg class="ico" aria-hidden="true"><use href="${ICONS}#${on ? "volume" : "volume-off"}"></use></svg><span>${on ? "Son activé" : "Son coupé"}</span>`;
        if (!on) audioStop(300);
        else if (phase !== "idle") audioInit();
    }

    /* ------------------------------------------------------------------
       Dessin
       ------------------------------------------------------------------ */
    function drawBackground(holeR) {
        ctx.beginPath();
        ctx.rect(0, 0, W, H);
        if (holeR > 0) hexPath(ctx, G.cx, G.cy, holeR);          // trou hexagonal : la page apparaît dedans
        ctx.fillStyle = C.propolis;
        ctx.fill("evenodd");

        ctx.save();
        ctx.beginPath(); ctx.rect(0, 0, W, H); if (holeR > 0) hexPath(ctx, G.cx, G.cy, holeR);
        ctx.clip("evenodd");
        ctx.strokeStyle = "rgba(233, 185, 73, .06)"; ctx.lineWidth = 1;
        ctx.beginPath();
        for (const c of G.cells) hexPath(ctx, c.x, c.y, 27);
        ctx.stroke();
        ctx.restore();

        if (holeR > 0) {                                           // bord de l'alvéole
            ctx.beginPath(); hexPath(ctx, G.cx, G.cy, holeR);
            ctx.strokeStyle = C.honey; ctx.lineWidth = 4; ctx.stroke();
        }
    }

    function drawGhost(alpha) {                                    // hexagone en pointillés avant le tracé
        ctx.save();
        ctx.setLineDash([3, 10]); ctx.lineCap = "round";
        ctx.strokeStyle = `rgba(233, 185, 73, ${0.28 * alpha})`; ctx.lineWidth = 2;
        ctx.beginPath(); hexPath(ctx, G.cx, G.cy, G.R); ctx.stroke();
        ctx.restore();
    }

    function drawTrail(u, alpha, scale) {
        if (u <= 0 || alpha <= 0) return;
        ctx.save();
        ctx.globalAlpha = alpha;
        ctx.translate(G.cx, G.cy); ctx.scale(scale, scale); ctx.translate(-G.cx, -G.cy);
        ctx.lineCap = "round"; ctx.lineJoin = "round";
        ctx.shadowColor = "rgba(233, 185, 73, .8)"; ctx.shadowBlur = 16;
        ctx.strokeStyle = C.honey; ctx.lineWidth = 5 / scale;
        ctx.beginPath();
        ctx.moveTo(G.v[0].x, G.v[0].y);
        const steps = Math.ceil(u * 6 * 12);
        for (let s = 1; s <= steps; s++) { const p = perimeter(Math.min(u, s / 72)); ctx.lineTo(p.x, p.y); }
        ctx.stroke();
        ctx.restore();
    }

    function drawFill(level, t, alpha, scale) {                    // miel qui monte dans l'alvéole
        if (level <= 0 || alpha <= 0) return;
        const R = G.R * scale;
        ctx.save();
        ctx.globalAlpha = alpha;
        ctx.beginPath(); hexPath(ctx, G.cx, G.cy, R - 2); ctx.clip();
        const top = G.cy + R - level * 2 * R;
        const grad = ctx.createLinearGradient(0, top, 0, G.cy + R);
        grad.addColorStop(0, C.honey2); grad.addColorStop(1, C.deep);
        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.moveTo(G.cx - R, G.cy + R);
        for (let x = -R; x <= R; x += 6) {
            const y = top + Math.sin(x / R * 5 + t / 180) * (level < 1 ? 5 : 2);
            ctx.lineTo(G.cx + x, y);
        }
        ctx.lineTo(G.cx + R, G.cy + R);
        ctx.closePath(); ctx.fill();
        ctx.restore();
    }

    function drawLogo(alpha, scale) {
        if (alpha <= 0 || !logo.complete) return;
        const s = G.R * 2 * (48 / 44) * scale;                    // le logo SVG a un hexagone de rayon 22 dans 48
        ctx.save(); ctx.globalAlpha = alpha;
        ctx.drawImage(logo, G.cx - s / 2, G.cy - s / 2, s, s);
        ctx.restore();
    }

    function drawSparks(dt) {
        for (let i = sparks.length - 1; i >= 0; i--) {
            const p = sparks[i];
            p.life -= dt; p.y += p.vy * dt / 16; p.x += p.vx * dt / 16;
            if (p.life <= 0) { sparks.splice(i, 1); continue; }
            ctx.globalAlpha = p.life / p.max;
            ctx.fillStyle = C.honey2;
            ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2); ctx.fill();
        }
        ctx.globalAlpha = 1;
    }
    function emit(x, y) {
        sparks.push({ x: x + (Math.random() - .5) * 6, y: y + 6, vx: (Math.random() - .5) * .6, vy: .4 + Math.random() * .8, r: 1 + Math.random() * 2.2, life: 700, max: 700 });
    }

    /* ------------------------------------------------------------------
       Position de l'abeille selon le temps (chorégraphie)
       ------------------------------------------------------------------ */
    let restPos = { x: 0, y: 0 }, landPos = null;

    function beeAt(t) {
        if (t < T.draw) {                                          // décollage depuis le bouton
            const k = ease(t / T.draw);
            return bezier(restPos, { x: G.cx - G.R * 1.9, y: G.cy + G.R * 0.4 }, G.v[0], k);
        }
        if (t < T.toWord) {                                        // tracé de l'hexagone
            const u = ease((t - T.draw) / (T.toWord - T.draw));
            const p = perimeter(u);
            return { x: p.x, y: p.y - 4 + Math.sin(t / 60) * 2, u };
        }
        const wl = { x: G.word.left - 6, y: G.word.top + G.word.h * 0.55 };
        if (t < T.write) {                                         // vers le début du mot
            const k = ease((t - T.toWord) / (T.write - T.toWord));
            return bezier(G.v[0], { x: G.cx - G.R * 2, y: G.cy }, wl, k);
        }
        if (t < T.fill) {                                          // écriture de « BeeFlow »
            const k = (t - T.write) / (T.fill - T.write);
            const x = lerp(G.word.left - 6, G.word.right + 8, k);
            const y = wl.y + Math.sin(k * Math.PI * 9) * G.word.h * 0.22 - Math.sin(k * Math.PI) * 6;
            return { x, y, write: k };
        }
        const hover = { x: G.cx + G.R * 0.9, y: G.cy - G.R - 34 };
        if (t < T.dive) {                                          // l'abeille regarde l'alvéole se remplir
            const k = ease(clamp01((t - T.fill) / 700));
            const from = { x: G.word.right + 8, y: wl.y };
            const p = bezier(from, { x: G.word.right + 60, y: G.cy }, hover, k);
            return { x: p.x + Math.sin(t / 240) * 6 * k, y: p.y + Math.cos(t / 300) * 5 * k };
        }
        if (!landPos) landPos = ctaPoint();
        if (t < T.land) {                                          // vers le bouton de la page d'accueil
            const k = ease((t - T.dive) / (T.land - T.dive));
            return bezier(hover, { x: lerp(hover.x, landPos.x, .5), y: Math.min(hover.y, landPos.y) - 120 }, landPos, k);
        }
        if (t < T.leave) return { x: landPos.x, y: landPos.y, rest: true };
        const k = ease(clamp01((t - T.leave) / (T.end - T.leave)));   // elle repart
        return bezier(landPos, { x: landPos.x + 160, y: landPos.y - 40 }, { x: W + 80, y: -80 }, k);
    }

    /* ------------------------------------------------------------------
       Boucle
       ------------------------------------------------------------------ */
    let last = 0, chimed = false, poured = false, whooshed = false, landed = false, removed = false;

    function placeBee(p, dt) {
        const dx = p.x - bee.x, dy = p.y - bee.y, speed = Math.hypot(dx, dy) / Math.max(dt / 16, .5);
        let target = bee.rot;
        if (p.rest) target = 0;
        else if (speed > 0.4) target = Math.atan2(dy, dx) * 180 / Math.PI + 90;
        let d = ((target - bee.rot) % 360 + 540) % 360 - 180;     // rotation la plus courte
        bee.rot += d * 0.2;
        bee.x = p.x; bee.y = p.y;
        beeEl.style.transform = `translate(${bee.x}px, ${bee.y}px) rotate(${bee.rot}deg) scale(${bee.scale})`;
        beeEl.classList.toggle("is-resting", !!p.rest);
        audioBee(speed, bee.x, !!p.rest);
    }

    function frame(now) {
        const dt = Math.min(50, now - (last || now)); last = now;
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        ctx.clearRect(0, 0, W, H);

        if (phase === "idle") {
            drawBackground(0);
            drawGhost(1);
            // l'abeille attend, posée sur le bouton, et respire
            const r = btnEnter.getBoundingClientRect();
            restPos = { x: r.right - 22, y: r.top - 12 };
            placeBee({ x: restPos.x, y: restPos.y + Math.sin(now / 400) * 2, rest: true }, dt);
            rafId = requestAnimationFrame(frame);
            return;
        }

        const t = now - tStart;
        let holeR = 0;
        if (t >= T.dive) {
            const k = clamp01((t - T.dive) / 1100);
            holeR = G.R * Math.pow(Math.hypot(W, H) / G.R * 1.15, ease(k));   // croissance exponentielle
            if (!whooshed) { whooshed = true; audioWhoosh(); intro.classList.add("is-diving"); document.documentElement.classList.remove("intro-active"); }
        }
        if (holeR < Math.hypot(W, H) * 1.1) {
            drawBackground(holeR);
            if (t < T.fill) drawGhost(1 - clamp01((t - T.draw) / 400));
            // pendant la plongée, le tracé, le miel et le logo grandissent avec l'alvéole et s'effacent
            const diveK = clamp01((t - T.dive) / 500);
            const sc = holeR > 0 ? holeR / G.R : 1;
            drawTrail(t < T.draw ? 0 : t < T.toWord ? (beeAt(t).u || 0) : 1, 1 - diveK, sc);

            // remplissage et logo
            const fk = clamp01((t - T.fill) / 1200);
            if (fk > 0 && !poured) { poured = true; audioPour(); }
            drawFill(ease(fk), t, 1 - diveK, sc);
            const lk = clamp01((t - (T.fill + 900)) / 500);
            if (lk > 0 && !chimed) { chimed = true; audioChime(); intro.classList.add("is-tagline"); }
            drawLogo(lk * (1 - diveK), (0.92 + lk * 0.08) * sc);
        } else if (!removed) {
            removed = true;
            canvas.style.display = "none";
            intro.style.visibility = "hidden";
        }

        // révélation du mot pendant l'écriture
        const p = beeAt(t);
        if (p.write !== undefined) word.style.clipPath = `inset(-20% ${100 - clamp01((p.x - G.word.left) / (G.word.right - G.word.left)) * 100}% -20% 0)`;
        else if (t >= T.fill) word.style.clipPath = "inset(-20% 0 -20% 0)";

        const drawing = (t > T.draw && t < T.toWord) || p.write !== undefined;
        audioScratch(drawing);
        if (drawing || (t > T.takeoff + 200 && t < T.draw)) emit(p.x, p.y);
        drawSparks(dt);

        if (t > T.land && !landed) { landed = true; audioBlip(); }
        bee.scale = t > T.dive && t < T.land ? lerp(1.15, 1, ease((t - T.dive) / (T.land - T.dive))) : 1;
        placeBee(p, dt);

        if (t >= T.end) return finish();
        rafId = requestAnimationFrame(frame);
    }

    /* ------------------------------------------------------------------
       Scénario
       ------------------------------------------------------------------ */
    function play() {
        if (phase !== "idle") return;
        phase = "play";
        intro.classList.add("is-playing");
        audioInit();
        tStart = performance.now();
    }

    function finish() {
        phase = "done";
        cancelAnimationFrame(rafId);
        audioStop(400);
        try { sessionStorage.setItem("beeflow_intro_vue", "1"); } catch (e) {}
        document.documentElement.classList.remove("intro-active");
        intro.remove(); beeEl.remove();
        window.removeEventListener("resize", layout);
    }

    function skip() {
        if (phase === "idle") { finish(); return; }
        // on saute directement à la plongée dans l'alvéole
        const now = performance.now();
        if (now - tStart < T.dive) tStart = now - T.dive;
        audioScratch(false);
    }

    /* ------------------------------------------------------------------
       Démarrage
       ------------------------------------------------------------------ */
    layout();
    window.addEventListener("resize", layout);
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(layout);   // largeur exacte du mot
    intro.classList.add("is-ready");
    setSound(soundOn);
    rafId = requestAnimationFrame(frame);

    btnEnter.addEventListener("click", play);
    btnSkip.addEventListener("click", skip);
    btnSound.addEventListener("click", () => setSound(!soundOn));
    document.addEventListener("keydown", e => { if (e.key === "Escape" && document.getElementById("intro")) skip(); });
})();
