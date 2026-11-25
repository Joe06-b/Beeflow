import * as THREE from "../../vendor/three/0.187.0/three.module.js";
import { createDiorama } from "./diorama.js";
import { createNaturalAnimations } from "./nature.js";
import { createWeatherEffects } from "./weather_effects.js";

const SCENE_HEIGHT = 12.6;
const MAX_PIXEL_RATIO = 1.5;
const TARGET_FRAME_MS = 1000 / 30;

function weatherLabel(state) {
    if (!state) return "Conditions météo indisponibles";
    if (state.isSimulation) {
        return `Simulation DEBUG · ${weatherLabel({ ...state, isSimulation: false })}`;
    }
    if (state.active === false) return "Conditions météo indisponibles";
    if (state.category === "storm") return "Orage";
    if (state.category === "fog") return "Brouillard";
    if (state.rain > 0) return "Précipitations en cours";
    if (state.isNight) return "Nuit sur le rucher";
    if (state.category === "cloudy") return "Ciel nuageux";
    if (state.category === "clear") return "Ciel dégagé";
    return "Paysage météo";
}

function disposeScene(scene) {
    const geometries = new Set();
    const materialSet = new Set();
    const textures = new Set();
    scene.traverse(object => {
        if (object.geometry) geometries.add(object.geometry);
        if (!object.material) return;
        const objectMaterials = Array.isArray(object.material)
            ? object.material
            : [object.material];
        objectMaterials.forEach(material => {
            if (materialSet.has(material)) return;
            materialSet.add(material);
            Object.values(material).forEach(value => {
                if (value && value.isTexture) textures.add(value);
            });
        });
    });
    geometries.forEach(geometry => geometry.dispose());
    textures.forEach(texture => texture.dispose());
    materialSet.forEach(material => material.dispose());
}

export function createMeteoScene(container, options = {}) {
    const canvas = container.querySelector("canvas");
    const fallback = container.querySelector("[data-scene-fallback]");
    const fallbackLabel = container.querySelector("[data-scene-fallback-label]");
    const reducedMotionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    let reducedMotion = reducedMotionQuery.matches;
    const debugPerformance = options.debug === true;
    let renderer;
    let resizeObserver;
    let intersectionObserver;
    let animationFrame = 0;
    let disposed = false;
    let contextLost = false;
    let pageSuspended = false;
    let intersecting = true;
    let elapsed = 0;
    let lastFrame = 0;
    let azimuth = Math.PI / 4;
    let zoom = 1;
    let pointerX = null;
    let scene;
    let camera;
    let diorama;
    let nature;
    let weather;
    let sunLight;
    let hemisphere;
    let fillLight;
    let currentWeather = { active: false };
    let currentZoneKey = "";
    let fpsStart = null;
    let fpsFrames = 0;
    let measuredFps = null;

    function showFallback(message) {
        container.dataset.sceneAvailable = "false";
        if (canvas) canvas.hidden = true;
        if (fallback) fallback.hidden = false;
        if (fallbackLabel) fallbackLabel.textContent = message;
    }

    function cancelAnimation() {
        if (animationFrame) window.cancelAnimationFrame(animationFrame);
        animationFrame = 0;
    }

    function resetFpsMeasurement() {
        fpsStart = null;
        fpsFrames = 0;
        measuredFps = null;
    }

    function publishPerformance(timestamp) {
        if (!debugPerformance || !renderer) return;
        if (Number.isFinite(timestamp)) {
            if (fpsStart === null) fpsStart = timestamp;
            fpsFrames += 1;
            const duration = timestamp - fpsStart;
            if (duration >= 1000) {
                measuredFps = fpsFrames * 1000 / duration;
                fpsStart = timestamp;
                fpsFrames = 0;
            }
        }
        const { render: renderInfo, memory } = renderer.info;
        container.dataset.meteoPerformance = JSON.stringify({
            fps: measuredFps === null ? null : Number(measuredFps.toFixed(1)),
            calls: renderInfo.calls,
            triangles: renderInfo.triangles,
            points: renderInfo.points,
            lines: renderInfo.lines,
            geometries: memory.geometries,
            textures: memory.textures,
        });
    }

    function renderScene(timestamp) {
        if (disposed || contextLost || !renderer) return;
        renderer.render(scene, camera);
        publishPerformance(timestamp);
    }

    if (!canvas) {
        showFallback("La scène 3D n'a pas pu être initialisée.");
        return { setWeather() {}, dispose() {} };
    }

    try {
        const context = canvas.getContext("webgl2", {
            alpha: false,
            antialias: true,
            powerPreference: "low-power",
        });
        if (!context) throw new Error("WebGL2 indisponible.");
        renderer = new THREE.WebGLRenderer({
            canvas,
            context,
            antialias: true,
            powerPreference: "low-power",
            alpha: false,
        });
    } catch (error) {
        showFallback("La scène 3D n'est pas prise en charge par ce navigateur ou cet appareil.");
        return { setWeather() {}, dispose() {} };
    }

    container.dataset.sceneAvailable = "true";
    if (fallback) fallback.hidden = true;
    canvas.hidden = false;

    scene = new THREE.Scene();
    scene.background = new THREE.Color("#d9e3da");

    camera = new THREE.OrthographicCamera(-9, 9, 6.3, -6.3, 0.1, 80);
    const target = new THREE.Vector3(0, 1.0, 0);
    const cameraRadius = 26;
    const cameraPolar = 0.7;

    function placeCamera() {
        camera.position.set(
            target.x + cameraRadius * Math.sin(cameraPolar) * Math.sin(azimuth),
            target.y + cameraRadius * Math.cos(cameraPolar),
            target.z + cameraRadius * Math.sin(cameraPolar) * Math.cos(azimuth),
        );
        camera.lookAt(target);
    }
    placeCamera();

    hemisphere = new THREE.HemisphereLight("#f5f0df", "#75805d", 1.45);
    scene.add(hemisphere);
    sunLight = new THREE.DirectionalLight("#ffe5af", 2.0);
    sunLight.position.set(-7, 13, 8);
    sunLight.castShadow = true;
    sunLight.shadow.mapSize.set(1024, 1024);
    sunLight.shadow.camera.left = -12;
    sunLight.shadow.camera.right = 12;
    sunLight.shadow.camera.top = 12;
    sunLight.shadow.camera.bottom = -12;
    sunLight.shadow.bias = -0.0005;
    scene.add(sunLight);

    fillLight = new THREE.DirectionalLight("#d6dfd0", 0.45);
    fillLight.position.set(6, 8, -8);
    scene.add(fillLight);

    diorama = createDiorama(THREE, scene);
    nature = createNaturalAnimations(diorama);
    weather = createWeatherEffects(THREE, scene, {
        sunLight,
        hemisphere,
        fillLight,
    });
    nature.setWeather({ active: false, windSpeed: 0, isNight: true });

    function zoneKey(zone) {
        return JSON.stringify([
            zone?.id,
            zone?.name,
            zone?.latitude,
            zone?.longitude,
            zone?.environment?.vegetation_type,
            zone?.environment?.surface_hectares,
            zone?.environment?.bloom_level,
        ]);
    }

    function setZone(zone) {
        if (disposed || !zone) return;
        const key = zoneKey(zone);
        if (key === currentZoneKey) return;

        if (diorama?.root) {
            scene.remove(diorama.root);
            disposeScene(diorama.root);
        }
        diorama = createDiorama(THREE, scene, zone);
        nature = createNaturalAnimations(diorama);
        currentZoneKey = key;
        currentWeather = { active: false };
        weather.setZone(zone);
        weather.setWeather(currentWeather);
        nature.setWeather(currentWeather);
        if (reducedMotion) {
            weather.update(1, elapsed, true);
            nature.update(1, true);
            renderScene();
        }
    }

    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.12;
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFShadowMap;
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, MAX_PIXEL_RATIO));

    function resize() {
        if (disposed || contextLost || !renderer) return;
        const bounds = container.getBoundingClientRect();
        const width = Math.max(1, Math.floor(bounds.width));
        const height = Math.max(1, Math.floor(bounds.height));
        renderer.setSize(width, height, false);
        const halfHeight = (SCENE_HEIGHT / 2) / zoom;
        const halfWidth = halfHeight * (width / height);
        camera.left = -halfWidth;
        camera.right = halfWidth;
        camera.top = halfHeight;
        camera.bottom = -halfHeight;
        camera.updateProjectionMatrix();
        if (reducedMotion) renderScene();
    }

    function schedule() {
        if (
            !disposed
            && !contextLost
            && !pageSuspended
            && !reducedMotion
            && !document.hidden
            && intersecting
            && !animationFrame
        ) {
            animationFrame = window.requestAnimationFrame(frame);
        }
    }

    function frame(timestamp) {
        animationFrame = 0;
        if (disposed || contextLost || pageSuspended || document.hidden || !intersecting) return;
        if (timestamp - lastFrame < TARGET_FRAME_MS) {
            schedule();
            return;
        }
        const delta = Math.min((timestamp - (lastFrame || timestamp)) / 1000, 0.05);
        lastFrame = timestamp;
        elapsed += delta;
        nature.update(delta, elapsed);
        weather.update(delta, elapsed);
        renderScene(timestamp);
        schedule();
    }

    function onVisibilityChange() {
        if (document.hidden) {
            cancelAnimation();
            resetFpsMeasurement();
        } else {
            lastFrame = 0;
            schedule();
        }
    }

    function onPointerDown(event) {
        if (event.button !== 0) return;
        pointerX = event.clientX;
        canvas.setPointerCapture?.(event.pointerId);
    }

    function onPointerMove(event) {
        if (pointerX === null) return;
        const delta = event.clientX - pointerX;
        pointerX = event.clientX;
        azimuth += delta * 0.006;
        placeCamera();
        if (reducedMotion) renderScene();
    }

    function onPointerUp() {
        pointerX = null;
    }

    function onWheel(event) {
        event.preventDefault();
        zoom = THREE.MathUtils.clamp(zoom * (event.deltaY < 0 ? 1.08 : 0.92), 0.76, 1.45);
        resize();
    }

    function dispose() {
        if (disposed) return;
        disposed = true;
        cancelAnimation();
        resizeObserver?.disconnect();
        intersectionObserver?.disconnect();
        canvas.removeEventListener("pointerdown", onPointerDown);
        canvas.removeEventListener("pointermove", onPointerMove);
        canvas.removeEventListener("pointerup", onPointerUp);
        canvas.removeEventListener("pointercancel", onPointerUp);
        canvas.removeEventListener("wheel", onWheel);
        canvas.removeEventListener("webglcontextlost", onContextLost, false);
        canvas.removeEventListener("webglcontextrestored", onContextRestored, false);
        window.removeEventListener("resize", resize);
        window.removeEventListener("pagehide", onPageHide);
        window.removeEventListener("pageshow", onPageShow);
        if (typeof reducedMotionQuery.removeEventListener === "function") {
            reducedMotionQuery.removeEventListener("change", onReducedMotionChange);
        } else {
            reducedMotionQuery.removeListener(onReducedMotionChange);
        }
        document.removeEventListener("visibilitychange", onVisibilityChange);
        disposeScene(scene);
        renderer.dispose();
    }

    function onContextLost(event) {
        event.preventDefault();
        contextLost = true;
        cancelAnimation();
        resetFpsMeasurement();
        container.dataset.sceneAvailable = "false";
        if (fallback) fallback.hidden = false;
        if (fallbackLabel) {
            fallbackLabel.textContent = "Le contexte WebGL a été interrompu. La scène reprendra lorsqu'il sera restauré.";
        }
    }

    function onContextRestored() {
        if (disposed) return;
        contextLost = false;
        resetFpsMeasurement();
        container.dataset.sceneAvailable = "true";
        if (fallback) fallback.hidden = true;
        canvas.hidden = false;
        resize();
        weather.update(0, elapsed, true);
        nature.update(0, true);
        renderScene();
        schedule();
    }

    function onReducedMotionChange(event) {
        reducedMotion = event.matches;
        if (reducedMotion) {
            cancelAnimation();
            resetFpsMeasurement();
            weather.update(0, elapsed, true);
            nature.update(0, true);
            renderScene();
        } else {
            lastFrame = 0;
            schedule();
        }
    }

    function onPageHide(event) {
        if (event.persisted) {
            pageSuspended = true;
            cancelAnimation();
            resetFpsMeasurement();
            return;
        }
        dispose();
    }

    function onPageShow(event) {
        if (!event.persisted || disposed) return;
        pageSuspended = false;
        lastFrame = 0;
        resetFpsMeasurement();
        resize();
        renderScene();
        schedule();
    }

    canvas.addEventListener("pointerdown", onPointerDown);
    canvas.addEventListener("pointermove", onPointerMove);
    canvas.addEventListener("pointerup", onPointerUp);
    canvas.addEventListener("pointercancel", onPointerUp);
    canvas.addEventListener("wheel", onWheel, { passive: false });
    canvas.addEventListener("webglcontextlost", onContextLost, false);
    canvas.addEventListener("webglcontextrestored", onContextRestored, false);
    window.addEventListener("resize", resize, { passive: true });
    window.addEventListener("pagehide", onPageHide);
    window.addEventListener("pageshow", onPageShow);
    if (typeof reducedMotionQuery.addEventListener === "function") {
        reducedMotionQuery.addEventListener("change", onReducedMotionChange);
    } else {
        reducedMotionQuery.addListener(onReducedMotionChange);
    }

    if ("ResizeObserver" in window) {
        resizeObserver = new ResizeObserver(resize);
        resizeObserver.observe(container);
    }
    if ("IntersectionObserver" in window) {
        intersectionObserver = new IntersectionObserver(entries => {
            intersecting = entries[0]?.isIntersecting ?? true;
            if (intersecting) schedule();
            else if (animationFrame) {
                window.cancelAnimationFrame(animationFrame);
                animationFrame = 0;
            }
        }, { threshold: 0.05 });
        intersectionObserver.observe(container);
    }

    document.addEventListener("visibilitychange", onVisibilityChange);
    resize();
    if (!reducedMotion) schedule();
    else renderScene();

    return {
        setWeather(state) {
            if (disposed || !weather || !state) return;
            currentWeather = state;
            container.dataset.weather = state.category || "unknown";
            container.setAttribute("aria-label", `Diorama météo : ${weatherLabel(state)}`);
            weather.setWeather(state);
            nature.setWeather(state);
            if (reducedMotion) {
                weather.update(0, elapsed, true);
                nature.update(0, true);
                renderScene();
            }
        },
        setZone,
        dispose,
    };
}
