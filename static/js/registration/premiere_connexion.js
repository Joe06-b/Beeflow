/* ==========================================================
   BEEFLOW — PREMIÈRE CONNEXION & CONFIGURATION DU COMPTE
   ========================================================== */

document.addEventListener('DOMContentLoaded', () => {

    // ============================================================
    //  1. CANVAS — ALVÉOLES INTERACTIVES + PARTICULES LUMINEUSES
    // ============================================================
    const canvas = document.getElementById('hiveCanvas');
    if (canvas) {
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
            if (particles.length > 50) return;
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
            }

            requestAnimationFrame(animate);
        }

        window.addEventListener('resize', resize);
        window.addEventListener('mousemove', e => { mouse.x = e.clientX; mouse.y = e.clientY; });
        window.addEventListener('mouseleave', () => { mouse.x = -1000; mouse.y = -1000; });
        resize();
        animate();
    }


    // ============================================================
    //  2. CURSEUR ABEILLE
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
    //  3. ABEILLES VOLANTES (SVG)
    // ============================================================
    const beesContainer = document.getElementById('flyingBees');
    if (beesContainer) {
        const BEE_SVG = `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 32 32"><g transform="rotate(-45 16 16)"><ellipse cx="11.5" cy="12" rx="5.2" ry="3.4" fill="#FFF9ED" stroke="#402817" stroke-width="1.3" transform="rotate(-25 11.5 12)"/><ellipse cx="20.5" cy="12" rx="5.2" ry="3.4" fill="#FFF9ED" stroke="#402817" stroke-width="1.3" transform="rotate(25 20.5 12)"/><ellipse cx="16" cy="18" rx="5.2" ry="7.6" fill="#E9B949" stroke="#402817" stroke-width="1.4"/><path d="M11.2 16.2h9.6M11 19.6h10M12.2 23h7.6" stroke="#402817" stroke-width="2"/><circle cx="16" cy="8.6" r="3.3" fill="#402817"/><path d="M14.6 6 13.4 3.4M17.4 6l1.2-2.6" stroke="#402817" stroke-width="1.2" stroke-linecap="round"/></g></svg>`;

        function createBee() {
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

        for (let i = 0; i < 4; i++) {
            setTimeout(() => createBee(), i * 2200);
        }
    }


    // ============================================================
    //  4. TOGGLE VISIBILITÉ MOTS DE PASSE
    // ============================================================
    document.querySelectorAll('.eye-toggle').forEach(toggleBtn => {
        toggleBtn.addEventListener('click', () => {
            const targetId = toggleBtn.getAttribute('data-target');
            const targetInput = document.getElementById(targetId);
            if (!targetInput) return;

            const isPassword = targetInput.type === 'password';
            targetInput.type = isPassword ? 'text' : 'password';

            const icoEye = toggleBtn.querySelector('.ico-eye');
            const icoEyeOff = toggleBtn.querySelector('.ico-eye-off');

            if (icoEye) icoEye.style.display = isPassword ? 'none' : 'block';
            if (icoEyeOff) icoEyeOff.style.display = isPassword ? 'block' : 'none';
        });
    });


    // ============================================================
    //  5. GESTION DU FACE ID SETUP (WEBCAM & CAPTURE)
    // ============================================================
    const btnStartCamera = document.getElementById('btnStartCamera');
    const btnCaptureFace = document.getElementById('btnCaptureFace');
    const btnRetakeFace = document.getElementById('btnRetakeFace');
    const faceSetupVideo = document.getElementById('faceSetupVideo');
    const faceSetupCanvas = document.getElementById('faceSetupCanvas');
    const faceCapturedThumb = document.getElementById('faceCapturedThumb');
    const faceSetupViewfinder = document.getElementById('faceSetupViewfinder');
    const setupCameraPlaceholder = document.getElementById('setupCameraPlaceholder');
    const setupFaceFeedback = document.getElementById('setupFaceFeedback');
    const faceDataInput = document.getElementById('faceData');
    const setupScannerLaser = document.getElementById('setupScannerLaser');

    let setupStream = null;

    function setSetupFeedback(type, text) {
        if (!setupFaceFeedback) return;
        setupFaceFeedback.className = 'face-feedback ' + type;
        setupFaceFeedback.textContent = text;
    }

    function stopSetupCamera() {
        if (setupStream) {
            setupStream.getTracks().forEach(track => track.stop());
            setupStream = null;
        }
        if (faceSetupVideo) faceSetupVideo.srcObject = null;
        if (setupScannerLaser) setupScannerLaser.style.display = 'none';
        if (faceSetupViewfinder) faceSetupViewfinder.classList.remove('is-scanning');
    }

    // Activer la caméra
    if (btnStartCamera) {
        btnStartCamera.addEventListener('click', async () => {
            try {
                setSetupFeedback('info', 'Démarrage de la caméra...');

                setupStream = await navigator.mediaDevices.getUserMedia({
                    video: {
                        facingMode: 'user',
                        width: { ideal: 640 },
                        height: { ideal: 480 }
                    },
                    audio: false
                });

                faceSetupVideo.srcObject = setupStream;
                faceSetupVideo.style.display = 'block';
                if (faceCapturedThumb) faceCapturedThumb.style.display = 'none';
                if (setupCameraPlaceholder) setupCameraPlaceholder.style.opacity = '0';

                await faceSetupVideo.play();

                btnStartCamera.style.display = 'none';
                btnCaptureFace.style.display = 'inline-flex';
                btnRetakeFace.style.display = 'none';

                setSetupFeedback('info', 'Placez votre visage au centre du cercle et souriez !');
            } catch (err) {
                console.error('Erreur webcam:', err);
                setSetupFeedback('error', 'Impossible d\'activer la caméra. Vérifiez les autorisations du navigateur.');
            }
        });
    }

    // Capturer la photo du visage
    if (btnCaptureFace) {
        btnCaptureFace.addEventListener('click', () => {
            if (!faceSetupVideo || !faceSetupCanvas) return;

            const w = faceSetupVideo.videoWidth || 640;
            const h = faceSetupVideo.videoHeight || 480;
            faceSetupCanvas.width = w;
            faceSetupCanvas.height = h;

            const ctx2d = faceSetupCanvas.getContext('2d');
            // Dessiner l'image (non inversée pour stockage fiable)
            ctx2d.drawImage(faceSetupVideo, 0, 0, w, h);

            const base64Data = faceSetupCanvas.toDataURL('image/jpeg', 0.88);

            // Enregistrer dans l'input masqué
            if (faceDataInput) {
                faceDataInput.value = base64Data;
            }

            // Afficher l'aperçu capturé
            if (faceCapturedThumb) {
                faceCapturedThumb.src = base64Data;
                faceCapturedThumb.style.display = 'block';
            }
            faceSetupVideo.style.display = 'none';

            // Animation succès
            if (faceSetupViewfinder) {
                faceSetupViewfinder.classList.add('is-success');
            }

            stopSetupCamera();

            btnCaptureFace.style.display = 'none';
            btnRetakeFace.style.display = 'inline-flex';

            setSetupFeedback('success', '✓ Visage capturé avec succès ! Votre Face ID sera configuré.');
        });
    }

    // Reprendre la photo
    if (btnRetakeFace) {
        btnRetakeFace.addEventListener('click', async () => {
            if (faceDataInput) faceDataInput.value = '';
            if (faceCapturedThumb) faceCapturedThumb.style.display = 'none';
            if (faceSetupViewfinder) faceSetupViewfinder.classList.remove('is-success', 'is-error');

            try {
                setupStream = await navigator.mediaDevices.getUserMedia({
                    video: {
                        facingMode: 'user',
                        width: { ideal: 640 },
                        height: { ideal: 480 }
                    },
                    audio: false
                });

                faceSetupVideo.srcObject = setupStream;
                faceSetupVideo.style.display = 'block';
                await faceSetupVideo.play();

                btnRetakeFace.style.display = 'none';
                btnCaptureFace.style.display = 'inline-flex';

                setSetupFeedback('info', 'Recentrez votre visage et cliquez sur Capturer.');
            } catch (err) {
                console.error(err);
                btnRetakeFace.style.display = 'none';
                btnStartCamera.style.display = 'inline-flex';
                setSetupFeedback('error', 'Erreur lors du redémarrage de la caméra.');
            }
        });
    }

    window.addEventListener('beforeunload', stopSetupCamera);


    // ============================================================
    //  6. VALIDATION DU FORMULAIRE ET SOUMISSION
    // ============================================================
    const premiereForm = document.getElementById('premiereConnexionForm');
    const newPassInput = document.getElementById('id_new_password1');
    const confirmPassInput = document.getElementById('id_new_password2');
    const btnSubmitFinal = document.getElementById('btnSubmitFinal');

    function setFieldErr(fieldId, msg) {
        const field = document.getElementById(fieldId);
        if (!field) return;
        field.classList.add('has-error');
        const errSpan = field.querySelector('.field-error');
        if (errSpan) errSpan.textContent = msg;
    }

    function clearFieldErr(fieldId) {
        const field = document.getElementById(fieldId);
        if (!field) return;
        field.classList.remove('has-error');
        const errSpan = field.querySelector('.field-error');
        if (errSpan) errSpan.textContent = '';
    }

    if (newPassInput) newPassInput.addEventListener('input', () => clearFieldErr('fieldNewPassword'));
    if (confirmPassInput) confirmPassInput.addEventListener('input', () => clearFieldErr('fieldConfirmPassword'));

    if (premiereForm) {
        premiereForm.addEventListener('submit', (e) => {
            let valid = true;

            const p1 = newPassInput ? newPassInput.value : '';
            const p2 = confirmPassInput ? confirmPassInput.value : '';

            if (!p1) {
                setFieldErr('fieldNewPassword', 'Veuillez saisir votre nouveau mot de passe.');
                valid = false;
            } else if (p1.length < 8) {
                setFieldErr('fieldNewPassword', 'Le mot de passe doit comporter au moins 8 caractères.');
                valid = false;
            }

            if (!p2) {
                setFieldErr('fieldConfirmPassword', 'Veuillez confirmer votre mot de passe.');
                valid = false;
            } else if (p1 && p2 && p1 !== p2) {
                setFieldErr('fieldConfirmPassword', 'Les deux mots de passe ne correspondent pas.');
                valid = false;
            }

            if (!valid) {
                e.preventDefault();
                premiereForm.classList.add('shake');
                setTimeout(() => premiereForm.classList.remove('shake'), 500);
                return;
            }

            if (btnSubmitFinal) {
                btnSubmitFinal.classList.add('is-loading');
            }
        });
    }


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
