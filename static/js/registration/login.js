/* ==========================================================
   BEEFLOW LOGIN — INTERACTIONS IMMERSIVES & AUTHENTIFICATION FACE ID
   ========================================================== */

document.addEventListener('DOMContentLoaded', () => {

    // ============================================================
    //  1. CANVAS — ALVÉOLES INTERACTIVES + PARTICULES LUMINEUSES
    // ============================================================
    const canvas = document.getElementById('hiveCanvas');
    const ctx = canvas.getContext('2d');
    let W, H, mouse = { x: -1000, y: -1000 };
    let hexagons = [];
    let particles = [];

    function resize() {
        W = canvas.width = window.innerWidth;
        H = canvas.height = window.innerHeight;
        buildHexGrid();
    }

    const HEX_SIZE = 40;
    const HEX_GAP = 6;

    function buildHexGrid() {
        hexagons = [];
        const w = (HEX_SIZE + HEX_GAP) * Math.sqrt(3);
        const h = (HEX_SIZE + HEX_GAP) * 1.5;
        const cols = Math.ceil(W / w) + 2;
        const rows = Math.ceil(H / h) + 2;

        for (let row = -1; row < rows; row++) {
            for (let col = -1; col < cols; col++) {
                const x = col * w + (row % 2 ? w / 2 : 0);
                const y = row * h;
                hexagons.push({
                    x, y,
                    baseOpacity: Math.random() * 0.03 + 0.01,
                    opacity: 0,
                    glow: 0,
                    pulseOffset: Math.random() * Math.PI * 2
                });
            }
        }
    }

    function drawHex(x, y, size) {
        ctx.beginPath();
        for (let i = 0; i < 6; i++) {
            const angle = Math.PI / 3 * i - Math.PI / 6;
            const px = x + size * Math.cos(angle);
            const py = y + size * Math.sin(angle);
            if (i === 0) ctx.moveTo(px, py);
            else ctx.lineTo(px, py);
        }
        ctx.closePath();
    }

    function spawnParticle() {
        if (particles.length > 60) return;
        particles.push({
            x: Math.random() * W,
            y: Math.random() * H,
            vx: (Math.random() - 0.5) * 0.3,
            vy: -Math.random() * 0.5 - 0.2,
            size: Math.random() * 2.5 + 0.5,
            life: 1,
            decay: Math.random() * 0.003 + 0.002,
            hue: 40 + Math.random() * 15
        });
    }

    let time = 0;
    function animate() {
        time += 0.008;
        ctx.clearRect(0, 0, W, H);

        const grad = ctx.createRadialGradient(W * 0.3, H * 0.4, 0, W * 0.3, H * 0.4, W * 0.8);
        grad.addColorStop(0, 'rgba(42, 28, 15, 0.3)');
        grad.addColorStop(1, 'rgba(15, 10, 6, 0)');
        ctx.fillStyle = grad;
        ctx.fillRect(0, 0, W, H);

        for (const hex of hexagons) {
            const dx = mouse.x - hex.x;
            const dy = mouse.y - hex.y;
            const dist = Math.sqrt(dx * dx + dy * dy);
            const radius = 200;

            const proximity = Math.max(0, 1 - dist / radius);
            const targetGlow = proximity * 0.35;
            hex.glow += (targetGlow - hex.glow) * 0.08;

            const pulse = Math.sin(time * 1.5 + hex.pulseOffset) * 0.015 + 0.015;
            hex.opacity = hex.baseOpacity + hex.glow + pulse;

            drawHex(hex.x, hex.y, HEX_SIZE);
            ctx.strokeStyle = `rgba(233, 185, 73, ${hex.opacity})`;
            ctx.lineWidth = 1;
            ctx.stroke();

            if (hex.glow > 0.02) {
                drawHex(hex.x, hex.y, HEX_SIZE);
                ctx.fillStyle = `rgba(233, 185, 73, ${hex.glow * 0.15})`;
                ctx.fill();
            }
        }

        if (Math.random() < 0.15) spawnParticle();

        for (let i = particles.length - 1; i >= 0; i--) {
            const p = particles[i];
            p.x += p.vx;
            p.y += p.vy;
            p.life -= p.decay;

            if (p.life <= 0) {
                particles.splice(i, 1);
                continue;
            }

            ctx.beginPath();
            ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
            ctx.fillStyle = `hsla(${p.hue}, 70%, 65%, ${p.life * 0.5})`;
            ctx.fill();

            ctx.beginPath();
            ctx.arc(p.x, p.y, p.size * 3, 0, Math.PI * 2);
            ctx.fillStyle = `hsla(${p.hue}, 70%, 65%, ${p.life * 0.08})`;
            ctx.fill();
        }

        requestAnimationFrame(animate);
    }

    window.addEventListener('resize', resize);
    window.addEventListener('mousemove', e => { mouse.x = e.clientX; mouse.y = e.clientY; });
    window.addEventListener('mouseleave', () => { mouse.x = -1000; mouse.y = -1000; });
    resize();
    animate();


    // ============================================================
    //  2. ABEILLES VOLANTES (SVG)
    // ============================================================
    const beesContainer = document.getElementById('flyingBees');
    const BEE_COUNT = 5;

    const BEE_SVG = `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 32 32"><g transform="rotate(-45 16 16)"><ellipse cx="11.5" cy="12" rx="5.2" ry="3.4" fill="#FFF9ED" stroke="#402817" stroke-width="1.3" transform="rotate(-25 11.5 12)"/><ellipse cx="20.5" cy="12" rx="5.2" ry="3.4" fill="#FFF9ED" stroke="#402817" stroke-width="1.3" transform="rotate(25 20.5 12)"/><ellipse cx="16" cy="18" rx="5.2" ry="7.6" fill="#E9B949" stroke="#402817" stroke-width="1.4"/><path d="M11.2 16.2h9.6M11 19.6h10M12.2 23h7.6" stroke="#402817" stroke-width="2"/><circle cx="16" cy="8.6" r="3.3" fill="#402817"/><path d="M14.6 6 13.4 3.4M17.4 6l1.2-2.6" stroke="#402817" stroke-width="1.2" stroke-linecap="round"/></g></svg>`;

    function createBee() {
        if (!beesContainer) return;
        const bee = document.createElement('div');
        bee.classList.add('bee');
        bee.innerHTML = BEE_SVG;

        const startX = Math.random() * window.innerWidth;
        const startY = Math.random() * window.innerHeight;
        const tx = (Math.random() - 0.5) * window.innerWidth * 0.8;
        const ty = (Math.random() - 0.5) * window.innerHeight * 0.6;
        const rot = (Math.random() - 0.5) * 60;
        const dur = Math.random() * 15 + 12;

        bee.style.left = startX + 'px';
        bee.style.top = startY + 'px';
        bee.style.setProperty('--tx', tx + 'px');
        bee.style.setProperty('--ty', ty + 'px');
        bee.style.setProperty('--rot', rot + 'deg');
        bee.style.animationDuration = dur + 's';
        bee.style.animationDelay = Math.random() * 8 + 's';
        const size = Math.random() * 12 + 18;
        bee.style.width = size + 'px';
        bee.style.height = size + 'px';

        beesContainer.appendChild(bee);

        bee.addEventListener('animationend', () => {
            bee.remove();
            createBee();
        });
    }

    if (beesContainer) {
        for (let i = 0; i < BEE_COUNT; i++) {
            setTimeout(() => createBee(), i * 2000);
        }
    }


    // ============================================================
    //  3. CURSEUR ABEILLE
    // ============================================================
    const beeCursor = document.getElementById('beeCursor');
    if (beeCursor) {
        let cursorX = -100, cursorY = -100;
        let beeX = -100, beeY = -100;
        let prevBeeX = -100, prevBeeY = -100;

        document.addEventListener('mousemove', e => {
            cursorX = e.clientX;
            cursorY = e.clientY;
        });

        document.addEventListener('mouseleave', () => {
            beeCursor.style.opacity = '0';
        });
        document.addEventListener('mouseenter', () => {
            beeCursor.style.opacity = '1';
        });

        function updateBeeCursor() {
            beeX += (cursorX - beeX) * 0.15;
            beeY += (cursorY - beeY) * 0.15;

            const dx = beeX - prevBeeX;
            const dy = beeY - prevBeeY;
            const speed = Math.sqrt(dx * dx + dy * dy);
            let angle = Math.atan2(dy, dx) * (180 / Math.PI);

            beeCursor.style.left = beeX + 'px';
            beeCursor.style.top = beeY + 'px';

            if (speed > 0.5) {
                beeCursor.style.transform = `translate(-50%, -50%) rotate(${angle + 90}deg)`;
            }

            prevBeeX = beeX;
            prevBeeY = beeY;
            requestAnimationFrame(updateBeeCursor);
        }
        requestAnimationFrame(updateBeeCursor);
    }


    // ============================================================
    //  4. GESTION DES ONGLETS (MOT DE PASSE vs FACE ID)
    // ============================================================
    const tabPassword = document.getElementById('tabPassword');
    const tabFace = document.getElementById('tabFace');
    const loginForm = document.getElementById('loginForm');
    const faceAuthPane = document.getElementById('faceAuthPane');

    let activeMediaStream = null;

    function stopCameraStream() {
        if (activeMediaStream) {
            activeMediaStream.getTracks().forEach(track => track.stop());
            activeMediaStream = null;
        }
        const video = document.getElementById('faceLoginVideo');
        if (video) video.srcObject = null;
        const viewfinder = document.getElementById('faceViewfinder');
        if (viewfinder) {
            viewfinder.classList.remove('is-scanning', 'is-success', 'is-error');
        }
        const placeholder = document.getElementById('cameraPlaceholder');
        if (placeholder) placeholder.style.opacity = '1';
    }

    if (tabPassword && tabFace && loginForm && faceAuthPane) {
        tabPassword.addEventListener('click', () => {
            tabPassword.classList.add('active');
            tabPassword.setAttribute('aria-selected', 'true');
            tabFace.classList.remove('active');
            tabFace.setAttribute('aria-selected', 'false');

            loginForm.style.display = 'block';
            faceAuthPane.style.display = 'none';

            stopCameraStream();
        });

        tabFace.addEventListener('click', () => {
            tabFace.classList.add('active');
            tabFace.setAttribute('aria-selected', 'true');
            tabPassword.classList.remove('active');
            tabPassword.setAttribute('aria-selected', 'false');

            loginForm.style.display = 'none';
            faceAuthPane.style.display = 'flex';
        });
    }


    // ============================================================
    //  5. FORMULAIRE MOT DE PASSE — INTERACTIONS & VALIDATION
    // ============================================================
    const form = document.getElementById('loginForm');
    const usernameIn = document.getElementById('username');
    const passIn = document.getElementById('password');
    const submitBtn = document.getElementById('btnSubmit');

    const eyeToggle = document.getElementById('eyeToggle');
    if (eyeToggle && passIn) {
        const icoEye = eyeToggle.querySelector('.ico-eye');
        const icoEyeOff = eyeToggle.querySelector('.ico-eye-off');

        eyeToggle.addEventListener('click', () => {
            const show = passIn.type === 'password';
            passIn.type = show ? 'text' : 'password';
            if (icoEye) icoEye.style.display = show ? 'none' : 'block';
            if (icoEyeOff) icoEyeOff.style.display = show ? 'block' : 'none';
        });
    }

    function setError(fieldId, msg) {
        const field = document.getElementById(fieldId);
        if (!field) return;
        field.classList.add('has-error');
        const errSpan = field.querySelector('.field-error');
        if (errSpan) errSpan.textContent = msg;
    }

    function clearError(fieldId) {
        const field = document.getElementById(fieldId);
        if (!field) return;
        field.classList.remove('has-error');
        const errSpan = field.querySelector('.field-error');
        if (errSpan) errSpan.textContent = '';
    }

    if (usernameIn) usernameIn.addEventListener('input', () => clearError('fieldUsername'));
    if (passIn) passIn.addEventListener('input', () => clearError('fieldPassword'));

    if (submitBtn) {
        submitBtn.addEventListener('mousedown', function (e) {
            const ripple = this.querySelector('.btn-ripple');
            if (!ripple) return;
            const rect = this.getBoundingClientRect();
            const size = Math.max(rect.width, rect.height) * 2;
            ripple.style.width = ripple.style.height = size + 'px';
            ripple.style.left = (e.clientX - rect.left - size / 2) + 'px';
            ripple.style.top = (e.clientY - rect.top - size / 2) + 'px';
            ripple.classList.remove('animate');
            void ripple.offsetWidth;
            ripple.classList.add('animate');
        });
    }

    if (form) {
        form.addEventListener('submit', e => {
            let ok = true;

            if (!usernameIn.value.trim()) {
                setError('fieldUsername', 'Le nom d\'utilisateur est requis');
                ok = false;
            }

            if (!passIn.value) {
                setError('fieldPassword', 'Le mot de passe est requis');
                ok = false;
            }

            if (!ok) {
                e.preventDefault();
                form.classList.add('shake');
                setTimeout(() => form.classList.remove('shake'), 500);
                return;
            }

            if (submitBtn) submitBtn.classList.add('is-loading');
        });
    }


    // ============================================================
    //  6. AUTHENTIFICATION FACE ID — WEBCAM & SCANNER
    // ============================================================
    const btnScanFace = document.getElementById('btnScanFace');
    const btnScanFaceText = document.getElementById('btnScanFaceText');
    const faceLoginVideo = document.getElementById('faceLoginVideo');
    const faceLoginCanvas = document.getElementById('faceLoginCanvas');
    const faceViewfinder = document.getElementById('faceViewfinder');
    const cameraPlaceholder = document.getElementById('cameraPlaceholder');
    const faceFeedback = document.getElementById('faceFeedback');

    function setFaceFeedback(type, text) {
        if (!faceFeedback) return;
        faceFeedback.className = 'face-feedback ' + type;
        faceFeedback.textContent = text;
    }

    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    let isScanningInProgress = false;

    async function startCameraAndScan() {
        if (isScanningInProgress) return;

        try {
            setFaceFeedback('info', 'Accès à la caméra en cours...');
            if (btnScanFaceText) btnScanFaceText.textContent = 'Démarrage caméra...';

            if (!activeMediaStream) {
                activeMediaStream = await navigator.mediaDevices.getUserMedia({
                    video: {
                        facingMode: 'user',
                        width: { ideal: 640 },
                        height: { ideal: 480 }
                    },
                    audio: false
                });

                faceLoginVideo.srcObject = activeMediaStream;
                await faceLoginVideo.play();
                if (cameraPlaceholder) cameraPlaceholder.style.opacity = '0';
            }

            // Démarrer l'animation de scan laser
            faceViewfinder.classList.remove('is-error', 'is-success');
            faceViewfinder.classList.add('is-scanning');
            setFaceFeedback('info', 'Analyse du visage en cours... Ne bougez pas.');
            if (btnScanFaceText) btnScanFaceText.textContent = 'Scan en cours...';
            isScanningInProgress = true;

            // Pause de 1.2s pour stabiliser l'exposition de la caméra
            setTimeout(() => {
                captureAndAuthenticate();
            }, 1200);

        } catch (err) {
            console.error('Erreur accès caméra:', err);
            faceViewfinder.classList.add('is-error');
            setFaceFeedback('error', 'Impossible d\'accéder à la caméra. Vérifiez les autorisations.');
            if (btnScanFaceText) btnScanFaceText.textContent = 'Réessayer';
            isScanningInProgress = false;
        }
    }

    async function captureAndAuthenticate() {
        try {
            if (!faceLoginVideo || !faceLoginCanvas) return;

            const w = faceLoginVideo.videoWidth || 640;
            const h = faceLoginVideo.videoHeight || 480;
            faceLoginCanvas.width = w;
            faceLoginCanvas.height = h;

            const ctx2d = faceLoginCanvas.getContext('2d');
            ctx2d.drawImage(faceLoginVideo, 0, 0, w, h);

            const imageDataBase64 = faceLoginCanvas.toDataURL('image/jpeg', 0.85);

            setFaceFeedback('info', 'Vérification biométrique auprès du rucher...');

            const csrfToken = getCookie('csrftoken') || (document.querySelector('[name=csrfmiddlewaretoken]') ? document.querySelector('[name=csrfmiddlewaretoken]').value : '');

            const response = await fetch('/comptes/login/face/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({ image: imageDataBase64 })
            });

            const result = await response.json();

            if (result.success) {
                faceViewfinder.classList.remove('is-scanning', 'is-error');
                faceViewfinder.classList.add('is-success');
                setFaceFeedback('success', `✓ Reconnu ! Bienvenue ${result.username} (${result.role})`);
                if (btnScanFaceText) btnScanFaceText.textContent = 'Connexion réussie !';

                stopCameraStream();

                setTimeout(() => {
                    window.location.href = result.redirect_url || '/';
                }, 800);

            } else {
                faceViewfinder.classList.remove('is-scanning');
                faceViewfinder.classList.add('is-error');
                setFaceFeedback('error', result.error || 'Visage non reconnu.');
                if (btnScanFaceText) btnScanFaceText.textContent = 'Recommencer le scan';
                isScanningInProgress = false;
            }

        } catch (err) {
            console.error('Erreur lors du scan Face ID:', err);
            faceViewfinder.classList.remove('is-scanning');
            faceViewfinder.classList.add('is-error');
            setFaceFeedback('error', 'Erreur de connexion au serveur. Réessayez.');
            if (btnScanFaceText) btnScanFaceText.textContent = 'Recommencer';
            isScanningInProgress = false;
        }
    }

    if (btnScanFace) {
        btnScanFace.addEventListener('click', () => {
            startCameraAndScan();
        });
    }

    // Arrêter la caméra lors de la fermeture ou du changement de page
    window.addEventListener('beforeunload', stopCameraStream);


    // ============================================================
    //  7. FOCUS GLOW SUR LA CARTE & PARALLAXE RUCHE 3D
    // ============================================================
    const card = document.querySelector('.form-card');
    if (card) {
        card.addEventListener('mousemove', e => {
            const rect = card.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            card.style.setProperty('--mx', x + 'px');
            card.style.setProperty('--my', y + 'px');
            card.style.background = `
                radial-gradient(circle 180px at ${x}px ${y}px, rgba(233,185,73,0.08), transparent),
                rgba(43, 27, 15, 0.82)
            `;
        });
        card.addEventListener('mouseleave', () => {
            card.style.background = 'rgba(43, 27, 15, 0.82)';
        });
    }

    const hiveStage = document.getElementById('hiveStage');
    if (hiveStage) {
        window.addEventListener('mousemove', e => {
            const dx = (e.clientX - window.innerWidth / 2) / (window.innerWidth / 2);
            const dy = (e.clientY - window.innerHeight / 2) / (window.innerHeight / 2);
            hiveStage.style.transform = `perspective(1100px) rotateY(${dx * 14}deg) rotateX(${-dy * 10}deg)`;
        });
        window.addEventListener('mouseleave', () => {
            hiveStage.style.transform = 'perspective(1100px) rotateY(0deg) rotateX(0deg)';
        });
    }

});
