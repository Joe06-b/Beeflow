import { terrainHeight } from "./diorama.js";

const TAU = Math.PI * 2;

function seededRandom(seed) {
    let value = seed >>> 0;
    return () => {
        value = (value * 1664525 + 1013904223) >>> 0;
        return value / 4294967296;
    };
}

function makeCloudLayers(THREE, scene) {
    const random = seededRandom(20261121);
    const geometry = new THREE.SphereGeometry(0.7, 12, 8);
    const dummy = new THREE.Object3D();
    const layers = [
        { clusters: 8, height: 8.1, depth: -7.2, scale: 0.78, speed: 0.72, opacity: 0.64 },
        { clusters: 9, height: 9.0, depth: -5.2, scale: 1.0, speed: 0.52, opacity: 0.78 },
        { clusters: 7, height: 8.4, depth: -2.7, scale: 1.2, speed: 0.36, opacity: 0.88 },
    ];

    return layers.map((layer, layerIndex) => {
        const clouds = [];
        for (let index = 0; index < layer.clusters; index += 1) {
            const lobeCount = 4 + Math.floor(random() * 3);
            clouds.push({
                x: -13 + (index + random() * 0.7) * (26 / layer.clusters),
                y: layer.height + (random() - 0.5) * 0.85,
                z: layer.depth + (random() - 0.5) * 1.8,
                scale: layer.scale * (0.72 + random() * 0.75),
                phase: random() * TAU,
                priority: (index + random() * 0.45) / layer.clusters,
                lobes: Array.from({ length: lobeCount }, (_, lobeIndex) => ({
                    x: (random() - 0.5) * (lobeIndex === 0 ? 0.2 : 1.45),
                    y: (random() - 0.5) * 0.4,
                    z: (random() - 0.5) * 0.7,
                    sx: 0.48 + random() * 0.85,
                    sy: 0.34 + random() * 0.42,
                    sz: 0.5 + random() * 0.65,
                })),
            });
        }

        const capacity = clouds.reduce((count, cloud) => count + cloud.lobes.length, 0);
        const material = new THREE.MeshStandardMaterial({
            color: "#f3f0e5",
            roughness: 1,
            transparent: true,
            opacity: 0,
            depthWrite: false,
        });
        const mesh = new THREE.InstancedMesh(geometry, material, capacity);
        mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
        mesh.frustumCulled = false;
        let instance = 0;
        clouds.forEach(cloud => {
            cloud.lobes.forEach(lobe => {
                const tint = 0.94 + random() * 0.12;
                mesh.setColorAt(instance++, new THREE.Color(tint, tint, tint * 0.98));
            });
        });
        const group = new THREE.Group();
        group.add(mesh);
        scene.add(group);
        return { ...layer, clouds, group, mesh, layerIndex };
    });
}

function makeSun(THREE, scene) {
    const sun = new THREE.Group();
    sun.visible = false;
    const orb = new THREE.Mesh(
        new THREE.SphereGeometry(0.62, 24, 16),
        new THREE.MeshBasicMaterial({
            color: "#f1d78f",
            transparent: true,
            opacity: 0,
        }),
    );
    sun.add(orb);

    const rayMaterial = new THREE.MeshBasicMaterial({
        color: "#eacb7e",
        transparent: true,
        opacity: 0.14,
        depthWrite: false,
    });
    for (let index = 0; index < 10; index += 1) {
        const ray = new THREE.Mesh(
            new THREE.CylinderGeometry(0.012, 0.045, 1.0, 5),
            rayMaterial,
        );
        const angle = (index / 10) * TAU;
        ray.position.set(Math.cos(angle) * 1.1, Math.sin(angle) * 1.1, 0);
        ray.rotation.z = -angle + Math.PI / 2;
        sun.add(ray);
    }
    scene.add(sun);
    return { group: sun, rayMaterial };
}

function makeMoonAndStars(THREE, scene) {
    const moon = new THREE.Group();
    moon.visible = false;
    const orb = new THREE.Mesh(
        new THREE.SphereGeometry(0.5, 20, 14),
        new THREE.MeshStandardMaterial({
            color: "#e8e4d3",
            roughness: 0.72,
            emissive: "#c5c6b7",
            emissiveIntensity: 0.18,
            transparent: true,
            opacity: 0,
        }),
    );
    moon.add(orb);
    scene.add(moon);

    const points = [];
    for (let index = 0; index < 70; index += 1) {
        const x = ((index * 37) % 29) - 14;
        const y = 6 + ((index * 19) % 11);
        const z = -7 - ((index * 11) % 8);
        points.push(x, y, z);
    }
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute("position", new THREE.Float32BufferAttribute(points, 3));
    const stars = new THREE.Points(
        geometry,
        new THREE.PointsMaterial({
            color: "#f1eddd",
            size: 0.055,
            transparent: true,
            opacity: 0,
            depthWrite: false,
        }),
    );
    scene.add(stars);
    return { moon, stars };
}

function makeRain(THREE, scene) {
    const count = 280;
    const positions = new Float32Array(count * 3);
    for (let index = 0; index < count; index += 1) {
        positions[index * 3] = (Math.random() - 0.5) * 17;
        positions[index * 3 + 1] = Math.random() * 9;
        positions[index * 3 + 2] = (Math.random() - 0.5) * 13;
    }
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    const points = new THREE.Points(
        geometry,
        new THREE.PointsMaterial({
            color: "#d8e0dc",
            size: 0.045,
            transparent: true,
            opacity: 0,
            depthWrite: false,
            sizeAttenuation: true,
        }),
    );
    points.visible = false;
    scene.add(points);

    const snowPositions = new Float32Array(220 * 3);
    for (let index = 0; index < 220; index += 1) {
        snowPositions[index * 3] = (Math.random() - 0.5) * 17;
        snowPositions[index * 3 + 1] = Math.random() * 9;
        snowPositions[index * 3 + 2] = (Math.random() - 0.5) * 13;
    }
    const snowGeometry = new THREE.BufferGeometry();
    snowGeometry.setAttribute(
        "position",
        new THREE.BufferAttribute(snowPositions, 3),
    );
    const snow = new THREE.Points(
        snowGeometry,
        new THREE.PointsMaterial({
            color: "#e8edf0",
            size: 0.075,
            transparent: true,
            opacity: 0,
            depthWrite: false,
            sizeAttenuation: true,
        }),
    );
    snow.visible = false;
    scene.add(snow);

    const puddles = [];
    for (const [x, z, scale] of [[-2.1, 2.3, 0.7], [2.4, -2.0, 0.85], [4.1, 1.3, 0.58]]) {
        const puddle = new THREE.Mesh(
            new THREE.CircleGeometry(0.55, 24),
            new THREE.MeshStandardMaterial({
                color: "#788b8a",
                roughness: 0.2,
                metalness: 0.14,
                transparent: true,
                opacity: 0,
                depthWrite: false,
            }),
        );
        puddle.rotation.x = -Math.PI / 2;
        puddle.position.set(x, terrainHeight(x, z) + 0.015, z);
        puddle.scale.set(scale, scale * 0.56, 1);
        puddle.visible = false;
        scene.add(puddle);
        puddles.push(puddle);
    }
    return {
        points,
        geometry,
        positions,
        puddles,
        snow,
        snowGeometry,
        snowPositions,
    };
}

function smoothstep(start, end, value) {
    const amount = THREEClamp((value - start) / (end - start));
    return amount * amount * (3 - 2 * amount);
}

function THREEClamp(value) {
    return Math.max(0, Math.min(1, value));
}

export function createWeatherEffects(THREE, scene, lights) {
    const { sunLight, hemisphere, fillLight } = lights;
    const dummy = new THREE.Object3D();
    const cloudLayers = makeCloudLayers(THREE, scene);
    const sun = makeSun(THREE, scene);
    const night = makeMoonAndStars(THREE, scene);
    const rain = makeRain(THREE, scene);
    const lightning = new THREE.PointLight("#dce8f0", 0, 28, 1.8);
    lightning.position.set(-1, 7, -2);
    scene.add(lightning);

    const skyDay = new THREE.Color("#a8c4d2");
    const skyNight = new THREE.Color("#172536");
    const skyTwilight = new THREE.Color("#d29a83");
    const skyStorm = new THREE.Color("#505d66");
    const fogDay = new THREE.Color("#d8dfd7");
    const sunWarm = new THREE.Color("#ffe5af");
    const sunCool = new THREE.Color("#d5e5f5");
    const twilightLight = new THREE.Color("#f5b98f");
    const stormLight = new THREE.Color("#aebbc4");
    const ambientDay = new THREE.Color("#dce8e7");
    const ambientNight = new THREE.Color("#9bacc4");
    const groundDay = new THREE.Color("#72805c");
    const groundNight = new THREE.Color("#27364a");
    const fillDay = new THREE.Color("#d6dfd0");
    const fillNight = new THREE.Color("#9bb2d0");
    const cloudDay = new THREE.Color("#f0eee7");
    const cloudNight = new THREE.Color("#71828f");
    const cloudTwilight = new THREE.Color("#d7a58d");
    const cloudStorm = new THREE.Color("#59656e");
    const scratchColor = new THREE.Color();
    scene.background = skyDay.clone();
    scene.fog = new THREE.FogExp2(fogDay.clone(), 0.007);

    const target = {
        active: false,
        cloudCover: 0,
        rainAmount: 0,
        snowAmount: 0,
        wind: 0,
        windDirection: 0,
        fog: 0,
        storm: 0,
        daylightFactor: 0.55,
        twilightFactor: 0,
        solarProgress: 0.5,
        temperatureCooling: 0,
    };
    const current = { ...target };
    let flashTimer = 4;
    let flashIntensity = 0;
    let surfaceScale = 1;

    function setWeather(state) {
        const category = state.category || "unknown";
        target.active = Boolean(state.active);
        const cover = Number.isFinite(state.cloudCover)
            ? THREE.MathUtils.clamp(state.cloudCover / 100, 0, 1)
            : 0;
        const amounts = [state.rain, state.precipitation]
            .filter(value => Number.isFinite(value) && value >= 0);
        const precipitation = amounts.length ? Math.max(...amounts) : null;
        const isRain = target.active
            && ["drizzle", "rain", "storm"].includes(category)
            && precipitation !== null
            && precipitation > 0;
        const isSnow = target.active && category === "snow";
        target.cloudCover = cover;
        target.rainAmount = isRain
            ? THREE.MathUtils.clamp(Math.sqrt(precipitation) / 2.4, 0.08, 1)
            : 0;
        target.snowAmount = isSnow
            ? precipitation > 0
                ? THREE.MathUtils.clamp(Math.sqrt(precipitation) / 1.8, 0.08, 1)
                : 0
            : 0;
        target.wind = Number.isFinite(state.windSpeed)
            ? THREE.MathUtils.clamp(state.windSpeed / 55, 0, 1)
            : 0;
        target.windDirection = Number.isFinite(state.windDirectionDegrees)
            ? ((state.windDirectionDegrees + 180) % 360) * Math.PI / 180
            : 0;
        target.fog = target.active && category === "fog" ? 0.82 : 0;
        target.storm = category === "storm" ? 1 : 0;
        target.daylightFactor = target.active
            && Number.isFinite(state.daylightFactor)
            ? THREE.MathUtils.clamp(state.daylightFactor, 0, 1)
            : 0.55;
        target.twilightFactor = target.active
            && Number.isFinite(state.twilightFactor)
            ? THREE.MathUtils.clamp(state.twilightFactor, 0, 1)
            : 0;
        target.solarProgress = Number.isFinite(state.solarProgress)
            ? THREE.MathUtils.clamp(state.solarProgress, 0, 1)
            : 0.5;
        target.temperatureCooling = Number.isFinite(state.temperatureC)
            ? THREE.MathUtils.clamp((12 - state.temperatureC) / 32, 0, 0.28)
            : 0;
    }

    function update(delta, elapsed, reducedMotion = false) {
        const blend = reducedMotion ? 1 : 1 - Math.exp(-delta * 1.35);
        for (const key of Object.keys(current)) {
            if (key === "active") {
                current.active += (Number(target.active) - current.active) * blend;
            } else {
                current[key] += (target[key] - current[key]) * blend;
            }
        }
        const active = current.active > 0.015;
        const day = current.daylightFactor;
        const twilight = current.twilightFactor;
        const storm = current.storm;
        const progress = current.solarProgress;
        const cloudiness = current.cloudCover;
        const background = scratchColor.copy(skyNight)
            .lerp(skyDay, day)
            .lerp(skyTwilight, twilight * 0.58)
            .lerp(skyStorm, storm * 0.72);
        if (active) scene.background.copy(background);
        else scene.background.set("#d9e3da");
        scene.fog.color.copy(fogDay)
            .lerp(skyNight, 1 - day)
            .lerp(skyTwilight, twilight * 0.42)
            .lerp(skyStorm, storm * 0.5);
        scene.fog.density = 0.005
            + current.fog * 0.034
            + current.rainAmount * 0.007
            + storm * 0.003;

        const cold = current.temperatureCooling;
        sunLight.position.set(
            -7 + 14 * progress,
            4.5 + Math.sin(progress * Math.PI) * 7.5,
            8,
        );
        sunLight.color.copy(scratchColor.copy(sunWarm)
            .lerp(sunCool, cold)
            .lerp(twilightLight, twilight * 0.4)
            .lerp(stormLight, storm * 0.65));
        sunLight.intensity = active
            ? 0.1 + day * (1.36 - cloudiness * 0.45) + twilight * 0.08
            : 0.55;
        hemisphere.color.copy(ambientDay).lerp(ambientNight, 1 - day);
        hemisphere.groundColor.copy(groundDay).lerp(groundNight, 1 - day);
        hemisphere.intensity = active ? 1.0 + day * 0.3 + twilight * 0.12 : 0.8;
        fillLight.color.copy(fillDay).lerp(fillNight, 1 - day);
        fillLight.intensity = active ? 0.45 + day * 0.1 + twilight * 0.08 : 0.3;

        sun.group.position.set(
            -7 + 14 * progress,
            4.0 + Math.sin(progress * Math.PI) * 7.5,
            -4.4,
        );
        const sunOpacity = active
            ? THREE.MathUtils.clamp(day * (1 - cloudiness * 0.72), 0, 1)
            : 0;
        sun.group.visible = sunOpacity > 0.02;
        sun.group.children[0].material.opacity = sunOpacity;
        sun.rayMaterial.opacity = sunOpacity * (1 - cloudiness) * 0.17;
        night.moon.position.set(6 - 12 * progress, 7.8, -5.2);
        const moonOpacity = active
            ? THREE.MathUtils.clamp((0.3 - day) / 0.3, 0, 1) * (1 - cloudiness * 0.72)
            : 0;
        night.moon.visible = moonOpacity > 0.02;
        night.moon.children[0].material.opacity = moonOpacity;
        night.stars.material.opacity = active
            ? THREE.MathUtils.clamp((0.12 - day) / 0.12, 0, 1) * (1 - cloudiness)
            : 0;

        const windX = Math.sin(current.windDirection);
        const windZ = Math.cos(current.windDirection);
        cloudLayers.forEach(layer => {
            const opacity = active
                ? (0.18 + cloudiness * 0.66) * layer.opacity
                : 0;
            layer.mesh.material.opacity = opacity;
            layer.mesh.visible = opacity > 0.015 && cloudiness > 0.015;
            layer.mesh.material.color.copy(scratchColor.copy(cloudDay)
                .lerp(cloudNight, 1 - day)
                .lerp(cloudTwilight, twilight * 0.3)
                .lerp(cloudStorm, storm * 0.88));

            if (layer.mesh.visible && !reducedMotion) {
                const speed = 0.035 + current.wind * 0.23;
                layer.clouds.forEach(cloud => {
                    cloud.x += windX * speed * layer.speed * delta;
                    cloud.z += windZ * speed * layer.speed * delta;
                    if (cloud.x > 14) cloud.x = -14;
                    else if (cloud.x < -14) cloud.x = 14;
                    if (cloud.z > -1.5) cloud.z = -9.2;
                    else if (cloud.z < -9.2) cloud.z = -1.5;
                });
            }

            if (layer.mesh.visible) {
                let instance = 0;
                layer.clouds.forEach(cloud => {
                    const weight = smoothstep(
                        cloud.priority - 0.08,
                        cloud.priority + 0.12,
                        cloudiness,
                    );
                    const bob = reducedMotion
                        ? 0
                        : Math.sin(elapsed * 0.12 * layer.speed + cloud.phase) * 0.075;
                    cloud.lobes.forEach(lobe => {
                        const visibleScale = Math.max(0.001, weight);
                        dummy.position.set(
                            cloud.x + lobe.x * cloud.scale * visibleScale,
                            cloud.y + bob + lobe.y * cloud.scale * visibleScale,
                            cloud.z + lobe.z * cloud.scale * visibleScale,
                        );
                        dummy.scale.set(
                            lobe.sx * cloud.scale * visibleScale,
                            lobe.sy * cloud.scale * visibleScale,
                            lobe.sz * cloud.scale * visibleScale,
                        );
                        dummy.rotation.set(0, cloud.phase * 0.08, 0);
                        dummy.updateMatrix();
                        layer.mesh.setMatrixAt(instance++, dummy.matrix);
                    });
                });
                layer.mesh.instanceMatrix.needsUpdate = true;
            }
        });

        const windAmount = current.wind;
        rain.points.visible = active && current.rainAmount > 0.015;
        rain.points.material.opacity = current.rainAmount * (0.56 + day * 0.2);
        rain.puddles.forEach((puddle, index) => {
            puddle.visible = active && current.rainAmount > 0.08;
            puddle.material.opacity = current.rainAmount * (0.18 + index * 0.035);
        });
        rain.snow.visible = active && current.snowAmount > 0.015;
        rain.snow.material.opacity = current.snowAmount * (0.58 + day * 0.15);
        if (!reducedMotion && (rain.points.visible || rain.snow.visible)) {
            const positions = rain.positions;
            const fallSpeed = 5 + current.rainAmount * 8;
            for (let index = 0; index < positions.length; index += 3) {
                positions[index + 1] -= delta * fallSpeed;
                positions[index] += delta * windX * (1.2 + windAmount);
                if (positions[index + 1] < 0.55) {
                    positions[index + 1] = 8.5 + (index % 7) * 0.2;
                    positions[index] = ((index * 37) % 1700) / 100 - 8.5;
                }
            }
            rain.geometry.attributes.position.needsUpdate = true;
            const snowPositions = rain.snowPositions;
            for (let index = 0; index < snowPositions.length; index += 3) {
                snowPositions[index + 1] -= delta * (0.75 + current.snowAmount * 0.8);
                snowPositions[index] += delta * windX * (0.35 + windAmount);
                snowPositions[index + 2] += delta * windZ * (0.35 + windAmount);
                if (snowPositions[index + 1] < 0.55) {
                    snowPositions[index + 1] = 8.7 + (index % 5) * 0.12;
                    snowPositions[index] = ((index * 31) % 1700) / 100 - 8.5;
                    snowPositions[index + 2] = ((index * 17) % 1300) / 100 - 6.5;
                }
            }
            rain.snowGeometry.attributes.position.needsUpdate = true;
        }

        if (active && storm > 0.72 && !reducedMotion) {
            flashTimer -= delta;
            if (flashTimer <= 0) {
                flashIntensity = (1.1 + Math.random() * 1.2) * storm;
                flashTimer = 2.5 + Math.random() * 5.5;
            }
        } else {
            flashIntensity = 0;
            flashTimer = 3.5;
        }
        flashIntensity = Math.max(0, flashIntensity - delta * 5.5);
        lightning.intensity = flashIntensity;
    }

    function setZone(zone) {
        const surface = Number(zone?.environment?.surface_hectares);
        surfaceScale = Number.isFinite(surface) && surface > 0
            ? Math.min(1.15, Math.max(0.85, Math.sqrt(surface / 4.5)))
            : 1;
        for (const puddle of rain.puddles) {
            const x = puddle.userData.baseX;
            const z = puddle.userData.baseZ;
            puddle.position.set(
                x * surfaceScale,
                terrainHeight(x * surfaceScale, z * surfaceScale) + 0.015,
                z * surfaceScale,
            );
            puddle.scale.set(
                puddle.userData.baseScale * surfaceScale,
                puddle.userData.baseScale * 0.56 * surfaceScale,
                1,
            );
        }
    }

    rain.puddles.forEach(puddle => {
        puddle.userData.baseX = puddle.position.x;
        puddle.userData.baseZ = puddle.position.z;
        puddle.userData.baseScale = puddle.scale.x;
    });

    return { setWeather, setZone, update };
}
