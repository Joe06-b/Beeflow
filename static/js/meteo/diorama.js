const TAU = Math.PI * 2;

function randomGenerator(seed) {
    let value = seed >>> 0;
    return () => {
        value = (value * 1664525 + 1013904223) >>> 0;
        return value / 4294967296;
    };
}

function zoneSeed(zone) {
    const identity = [
        zone?.id,
        zone?.name,
        zone?.latitude,
        zone?.longitude,
        zone?.environment?.vegetation_type,
    ].join("|");
    let hash = 2166136261;
    for (let index = 0; index < identity.length; index += 1) {
        hash ^= identity.charCodeAt(index);
        hash = Math.imul(hash, 16777619);
    }
    return hash >>> 0;
}

function zoneProfile(zone) {
    const environment = zone?.environment || {};
    const vegetation = environment.vegetation_type || "Prairie";
    const bloom = {
        Absente: 0,
        Faible: 0.3,
        Moyenne: 0.68,
        Abondante: 1,
    }[environment.bloom_level] ?? 0.5;
    const profiles = {
        Foret: {
            trees: 6,
            bushes: 2,
            grassDensity: 0.72,
            treeStyle: "evergreen",
            groundColor: "#dce1ce",
            leafColors: ["#536b50", "#61775a", "#718060", "#82906b"],
            flowerColors: ["#d9d3bb", "#b99c78", "#c5b779", "#e0d4bc"],
        },
        Maquis: {
            trees: 2,
            bushes: 7,
            grassDensity: 0.85,
            treeStyle: "broadleaf",
            groundColor: "#e1ddc2",
            leafColors: ["#65784e", "#78875a", "#566c48", "#879064"],
            flowerColors: ["#aa8ea2", "#c3a4b7", "#d0bc95", "#d4cbb6"],
        },
        Prairie: {
            trees: 3,
            bushes: 3,
            grassDensity: 1,
            treeStyle: "broadleaf",
            groundColor: "#e5ead0",
            leafColors: ["#697b4f", "#849064", "#63764b", "#92966d"],
            flowerColors: ["#d9b866", "#d9d3bb", "#b98168", "#c2a15d"],
        },
        Verger: {
            trees: 6,
            bushes: 2,
            grassDensity: 0.75,
            treeStyle: "orchard",
            groundColor: "#e3e1c8",
            leafColors: ["#65784e", "#78875a", "#566c48", "#879064"],
            flowerColors: ["#d8c1ad", "#d4b8aa", "#d4bd78", "#e3d6c1"],
        },
        Culture: {
            trees: 1,
            bushes: 1,
            grassDensity: 0.55,
            treeStyle: "broadleaf",
            groundColor: "#dedbbe",
            leafColors: ["#687850", "#7d8859", "#5e7047", "#8d9169"],
            flowerColors: ["#d2b774", "#c5ad8a", "#d4cbb6", "#b7a56f"],
        },
        Autre: {
            trees: 3,
            bushes: 3,
            grassDensity: 0.8,
            treeStyle: "broadleaf",
            groundColor: "#e1e4ce",
            leafColors: ["#65784e", "#78875a", "#566c48", "#879064"],
            flowerColors: ["#d9b866", "#d9d3bb", "#b98168", "#c2a15d"],
        },
    };
    const profile = profiles[vegetation] || profiles.Autre;
    const surface = Number(environment.surface_hectares);
    return {
        vegetation,
        bloom,
        surfaceScale: Number.isFinite(surface) && surface > 0
            ? Math.min(1.15, Math.max(0.85, Math.sqrt(surface / 4.5)))
            : 1,
        ...profile,
    };
}

function terrainHeight(x, z) {
    return 0.48
        + 0.12 * Math.sin(x * 0.48 + 0.3) * Math.cos(z * 0.62)
        + 0.06 * Math.sin(z * 1.1 + x * 0.2);
}

function insideTerrain(x, z, margin = 0) {
    const radius = 8.15 - margin;
    return Math.abs(z) <= radius * Math.sqrt(3) / 2
        && Math.abs(x) + Math.abs(z) / Math.sqrt(3) <= radius;
}

function clipTerrainGeometry(THREE, geometry) {
    const positions = geometry.attributes.position;
    const sourceIndices = geometry.index.array;
    const radius = 8.15;
    const boundary = [
        [radius, 0],
        [radius / 2, radius * Math.sqrt(3) / 2],
        [-radius / 2, radius * Math.sqrt(3) / 2],
        [-radius, 0],
        [-radius / 2, -radius * Math.sqrt(3) / 2],
        [radius / 2, -radius * Math.sqrt(3) / 2],
    ];
    const vertices = [];
    const indices = [];
    const vertexMap = new Map();
    const addVertex = point => {
        const key = point.map(value => Math.round(value * 100000)).join(",");
        if (!vertexMap.has(key)) {
            vertexMap.set(key, vertices.length / 3);
            vertices.push(...point);
        }
        return vertexMap.get(key);
    };

    for (let index = 0; index < sourceIndices.length; index += 3) {
        let polygon = [0, 1, 2].map(offset => {
            const vertex = sourceIndices[index + offset];
            return [
                positions.getX(vertex),
                positions.getY(vertex),
                positions.getZ(vertex),
            ];
        });

        for (let edge = 0; edge < boundary.length && polygon.length; edge += 1) {
            const start = boundary[edge];
            const end = boundary[(edge + 1) % boundary.length];
            const signedDistance = point =>
                (end[0] - start[0]) * (point[2] - start[1])
                - (end[1] - start[1]) * (point[0] - start[0]);
            const clipped = [];
            let previous = polygon[polygon.length - 1];
            let previousDistance = signedDistance(previous);

            for (const current of polygon) {
                const currentDistance = signedDistance(current);
                const previousInside = previousDistance >= -1e-8;
                const currentInside = currentDistance >= -1e-8;
                if (previousInside !== currentInside) {
                    const amount = previousDistance / (previousDistance - currentDistance);
                    clipped.push(previous.map((value, axis) =>
                        value + (current[axis] - value) * amount,
                    ));
                }
                if (currentInside) clipped.push(current);
                previous = current;
                previousDistance = currentDistance;
            }
            polygon = clipped;
        }

        for (let vertex = 1; vertex < polygon.length - 1; vertex += 1) {
            indices.push(
                addVertex(polygon[0]),
                addVertex(polygon[vertex]),
                addVertex(polygon[vertex + 1]),
            );
        }
    }

    const clippedGeometry = new THREE.BufferGeometry();
    clippedGeometry.setAttribute(
        "position",
        new THREE.Float32BufferAttribute(vertices, 3),
    );
    clippedGeometry.setIndex(indices);
    clippedGeometry.computeVertexNormals();
    geometry.dispose();
    return clippedGeometry;
}

function makeGroundTexture(THREE, random) {
    const canvas = document.createElement("canvas");
    canvas.width = 256;
    canvas.height = 256;
    const context = canvas.getContext("2d");
    context.fillStyle = "#65794f";
    context.fillRect(0, 0, canvas.width, canvas.height);
    for (let index = 0; index < 1400; index += 1) {
        const light = random() > 0.55;
        context.fillStyle = light
            ? `rgba(205, 197, 139, ${0.035 + random() * 0.065})`
            : `rgba(27, 49, 31, ${0.035 + random() * 0.075})`;
        const width = 1 + random() * 4;
        const height = 1 + random() * 7;
        context.fillRect(
            random() * canvas.width,
            random() * canvas.height,
            width,
            height,
        );
    }
    const texture = new THREE.CanvasTexture(canvas);
    texture.colorSpace = THREE.SRGBColorSpace;
    texture.wrapS = THREE.RepeatWrapping;
    texture.wrapT = THREE.RepeatWrapping;
    texture.repeat.set(3, 2);
    return texture;
}

function makeWoodTexture(THREE, random) {
    const canvas = document.createElement("canvas");
    canvas.width = 256;
    canvas.height = 128;
    const context = canvas.getContext("2d");
    context.fillStyle = "#a47b4e";
    context.fillRect(0, 0, canvas.width, canvas.height);
    for (let index = 0; index < 46; index += 1) {
        context.strokeStyle = `rgba(${random() > 0.5 ? "68, 43, 24" : "236, 201, 145"}, ${0.04 + random() * 0.09})`;
        context.lineWidth = 1 + random() * 3;
        context.beginPath();
        const y = random() * canvas.height;
        context.moveTo(0, y);
        context.bezierCurveTo(
            canvas.width * 0.3,
            y + random() * 8 - 4,
            canvas.width * 0.7,
            y + random() * 8 - 4,
            canvas.width,
            y + random() * 3 - 1.5,
        );
        context.stroke();
    }
    const texture = new THREE.CanvasTexture(canvas);
    texture.colorSpace = THREE.SRGBColorSpace;
    texture.wrapS = THREE.RepeatWrapping;
    texture.wrapT = THREE.RepeatWrapping;
    texture.repeat.set(1.3, 1);
    return texture;
}

function addTerrain(THREE, scene, material) {
    const soilMaterial = new THREE.MeshStandardMaterial({
        color: "#574b35",
        roughness: 0.9,
    });
    const geometry = new THREE.CylinderGeometry(8.15, 7.95, 0.46, 6, 1);
    const base = new THREE.Mesh(
        geometry,
        [soilMaterial, material, soilMaterial],
    );
    base.position.y = 0.05;
    base.receiveShadow = true;
    base.castShadow = true;
    scene.add(base);

    const top = new THREE.PlaneGeometry(15.7, 11.6, 64, 48);
    top.rotateX(-Math.PI / 2);
    const positions = top.attributes.position;
    for (let index = 0; index < positions.count; index += 1) {
        positions.setY(
            index,
            terrainHeight(positions.getX(index), positions.getZ(index)) - 0.48,
        );
    }
    const clippedTop = clipTerrainGeometry(THREE, top);
    const meadow = new THREE.Mesh(clippedTop, material);
    meadow.position.y = 0.48;
    meadow.receiveShadow = true;
    meadow.castShadow = false;
    scene.add(meadow);

    const rim = new THREE.Mesh(
        new THREE.CylinderGeometry(8.12, 8.0, 0.13, 6, 1, true),
        new THREE.MeshStandardMaterial({ color: "#748153", roughness: 0.88 }),
    );
    rim.position.y = 0.4;
    rim.castShadow = true;
    rim.receiveShadow = true;
    scene.add(rim);
}

function addHive(THREE, parent, x, z, scale, woodMaterial, darkWood, roofMaterial, index) {
    const hive = new THREE.Group();
    hive.position.set(x, terrainHeight(x, z), z);
    hive.scale.setScalar(scale);
    parent.add(hive);

    const postGeometry = new THREE.BoxGeometry(0.09, 0.28, 0.09);
    for (const [px, pz] of [[-0.47, -0.38], [0.47, -0.38], [-0.47, 0.38], [0.47, 0.38]]) {
        const foot = new THREE.Mesh(postGeometry, darkWood);
        foot.position.set(px, 0.14, pz);
        foot.castShadow = true;
        hive.add(foot);
    }

    const boxGeometry = new THREE.BoxGeometry(1.12, 0.42, 0.92);
    for (let level = 0; level < 3; level += 1) {
        const box = new THREE.Mesh(boxGeometry, woodMaterial);
        box.position.y = 0.38 + level * 0.42;
        box.castShadow = true;
        box.receiveShadow = true;
        hive.add(box);

        const band = new THREE.Mesh(
            new THREE.BoxGeometry(1.16, 0.035, 0.96),
            darkWood,
        );
        band.position.y = 0.17 + level * 0.42;
        band.castShadow = true;
        hive.add(band);

        for (const px of [-0.52, 0.52]) {
            const corner = new THREE.Mesh(
                new THREE.BoxGeometry(0.045, 0.39, 0.055),
                darkWood,
            );
            corner.position.set(px, 0.38 + level * 0.42, 0.45);
            hive.add(corner);
        }
    }

    const entrance = new THREE.Mesh(
        new THREE.BoxGeometry(0.3, 0.045, 0.025),
        new THREE.MeshStandardMaterial({ color: "#261f17", roughness: 1 }),
    );
    entrance.position.set(0, 0.42, 0.469);
    hive.add(entrance);

    const landing = new THREE.Mesh(
        new THREE.BoxGeometry(0.55, 0.055, 0.23),
        darkWood,
    );
    landing.position.set(0, 0.3, 0.54);
    landing.castShadow = true;
    hive.add(landing);

    const roofBase = new THREE.Mesh(
        new THREE.BoxGeometry(1.3, 0.12, 1.1),
        roofMaterial,
    );
    roofBase.position.y = 1.7;
    roofBase.castShadow = true;
    hive.add(roofBase);

    const roof = new THREE.Mesh(
        new THREE.ConeGeometry(0.86, 0.3, 4),
        roofMaterial,
    );
    roof.rotation.y = Math.PI / 4;
    roof.position.y = 1.89;
    roof.castShadow = true;
    hive.add(roof);

    const ridge = new THREE.Mesh(
        new THREE.BoxGeometry(0.13, 0.11, 1.18),
        darkWood,
    );
    ridge.position.set(0, 1.99, 0);
    ridge.castShadow = true;
    hive.add(ridge);

    const plaque = new THREE.Mesh(
        new THREE.BoxGeometry(0.24, 0.14, 0.025),
        new THREE.MeshStandardMaterial({ color: "#5c4931", roughness: 0.78 }),
    );
    plaque.position.set(0.31, 1.36, 0.47);
    hive.add(plaque);

    hive.userData.index = index;
    return hive;
}

function addTree(THREE, scene, x, z, scale, materials, seed, style) {
    const random = randomGenerator(seed);
    const tree = new THREE.Group();
    tree.position.set(x, terrainHeight(x, z), z);
    tree.scale.setScalar(scale);
    scene.add(tree);

    const trunk = new THREE.Mesh(
        new THREE.CylinderGeometry(0.1, 0.2, 1.5, 7, 3),
        materials.trunk,
    );
    trunk.position.y = 0.72;
    trunk.castShadow = true;
    tree.add(trunk);

    const branchGeometry = new THREE.CylinderGeometry(0.035, 0.07, 0.68, 5);
    for (let index = 0; index < 3; index += 1) {
        const branch = new THREE.Mesh(branchGeometry, materials.trunk);
        branch.position.set(
            (random() - 0.5) * 0.48,
            1.03 + random() * 0.34,
            (random() - 0.5) * 0.42,
        );
        branch.rotation.z = (random() - 0.5) * 1.15;
        branch.rotation.x = (random() - 0.5) * 0.8;
        branch.castShadow = false;
        tree.add(branch);
    }

    if (style === "evergreen") {
        for (let level = 0; level < 4; level += 1) {
            const foliage = new THREE.Mesh(
                new THREE.ConeGeometry(0.82 - level * 0.1, 1.05, 9, 2),
                materials.leaves[(level + Math.floor(random() * 3)) % materials.leaves.length],
            );
            foliage.position.set(
                (random() - 0.5) * 0.14,
                1.25 + level * 0.44,
                (random() - 0.5) * 0.14,
            );
            foliage.rotation.y = random() * TAU;
            foliage.castShadow = true;
            foliage.receiveShadow = true;
            tree.add(foliage);
        }
    } else {
        const foliageGeometry = new THREE.IcosahedronGeometry(
            style === "orchard" ? 0.64 : 0.58,
            1,
        );
        const foliageCount = style === "orchard" ? 10 : 8;
        for (let index = 0; index < foliageCount; index += 1) {
            const foliage = new THREE.Mesh(
                foliageGeometry,
                materials.leaves[index % materials.leaves.length],
            );
            foliage.position.set(
                (random() - 0.5) * (style === "orchard" ? 0.9 : 1.1),
                1.55 + random() * (style === "orchard" ? 0.55 : 0.75),
                (random() - 0.5) * 0.95,
            );
            foliage.scale.set(
                0.78 + random() * 0.44,
                0.75 + random() * 0.4,
                0.8 + random() * 0.4,
            );
            foliage.castShadow = true;
            foliage.receiveShadow = true;
            tree.add(foliage);
        }
    }
    tree.userData.baseRotation = (random() - 0.5) * 0.08;
    return tree;
}

function addBush(THREE, scene, x, z, scale, materials, seed) {
    const random = randomGenerator(seed);
    const bush = new THREE.Group();
    bush.position.set(x, terrainHeight(x, z), z);
    bush.scale.setScalar(scale);
    scene.add(bush);
    for (let index = 0; index < 8; index += 1) {
        const leaf = new THREE.Mesh(
            new THREE.IcosahedronGeometry(0.36 + random() * 0.16, 1),
            materials.leaves[index % materials.leaves.length],
        );
        leaf.position.set(
            (random() - 0.5) * 0.72,
            0.23 + random() * 0.42,
            (random() - 0.5) * 0.55,
        );
        leaf.castShadow = false;
        leaf.receiveShadow = true;
        bush.add(leaf);
    }
    return bush;
}

function addFlowers(THREE, scene, seed, profile) {
    const random = randomGenerator(seed);
    const patches = [];
    const flowerColors = profile.flowerColors;
    const petalGeometry = new THREE.SphereGeometry(1, 7, 5);
    const centerGeometry = new THREE.SphereGeometry(0.028, 7, 5);
    const stemGeometry = new THREE.CylinderGeometry(0.012, 0.019, 0.25, 5);
    const leafGeometry = new THREE.SphereGeometry(1, 6, 4);
    const stemMaterial = new THREE.MeshStandardMaterial({
        color: "#586d43",
        roughness: 0.95,
    });
    const leafMaterial = new THREE.MeshStandardMaterial({
        color: "#718451",
        roughness: 0.92,
    });
    const centerMaterial = new THREE.MeshStandardMaterial({
        color: "#8d632f",
        roughness: 0.86,
    });
    const dummy = new THREE.Object3D();

    const patchCount = Math.round(profile.bloom * 11);
    for (let patchIndex = 0; patchIndex < patchCount; patchIndex += 1) {
        const patch = new THREE.Group();
        let patchX;
        let patchZ;
        do {
            patchX = -5.1 + random() * 10.2;
            patchZ = -3.2 + random() * 6.4;
        } while (!insideTerrain(patchX, patchZ, 1.3));
        patch.position.set(patchX, terrainHeight(patchX, patchZ), patchZ);
        scene.add(patch);

        const count = 8 + Math.floor(random() * (12 + profile.bloom * 12));
        const stems = new THREE.InstancedMesh(stemGeometry, stemMaterial, count);
        const leaves = new THREE.InstancedMesh(leafGeometry, leafMaterial, count * 2);
        const centers = new THREE.InstancedMesh(centerGeometry, centerMaterial, count);
        const petals = flowerColors.map(color => new THREE.InstancedMesh(
            petalGeometry,
            new THREE.MeshStandardMaterial({
                color,
                roughness: 0.78,
                side: THREE.DoubleSide,
            }),
            count * 5,
        ));
        const petalCounts = petals.map(() => 0);
        let leafIndex = 0;

        for (let flower = 0; flower < count; flower += 1) {
            const x = (random() - 0.5) * 2.2;
            const z = (random() - 0.5) * 1.25;
            const height = 0.2 + random() * 0.22;

            dummy.position.set(x, height / 2, z);
            dummy.rotation.set(0, random() * TAU, 0);
            dummy.scale.set(1, height / 0.25, 1);
            dummy.updateMatrix();
            stems.setMatrixAt(flower, dummy.matrix);

            for (let side = 0; side < 2; side += 1) {
                const direction = side === 0 ? -1 : 1;
                dummy.position.set(
                    x + direction * 0.07,
                    height * (side === 0 ? 0.35 : 0.55),
                    z,
                );
                dummy.rotation.set(0, direction * 0.5, direction * 0.45);
                dummy.scale.set(0.1, 0.024, 0.045);
                dummy.updateMatrix();
                leaves.setMatrixAt(leafIndex++, dummy.matrix);
            }

            const type = Math.floor(random() * petals.length);
            const petalIndex = petalCounts[type]++;
            for (let petal = 0; petal < 5; petal += 1) {
                const angle = (petal / 5) * TAU;
                dummy.position.set(
                    x + Math.cos(angle) * 0.052,
                    height,
                    z + Math.sin(angle) * 0.052,
                );
                dummy.rotation.set(0, -angle, 0.3);
                dummy.scale.set(0.075, 0.025, 0.04);
                dummy.updateMatrix();
                petals[type].setMatrixAt(petalIndex * 5 + petal, dummy.matrix);
            }

            dummy.position.set(x, height + 0.012, z);
            dummy.rotation.set(0, 0, 0);
            dummy.scale.set(1, 1, 1);
            dummy.updateMatrix();
            centers.setMatrixAt(flower, dummy.matrix);
        }

        petals.forEach((mesh, index) => {
            mesh.count = petalCounts[index] * 5;
        });
        for (const mesh of [stems, leaves, centers, ...petals]) {
            mesh.instanceMatrix.needsUpdate = true;
            mesh.castShadow = false;
            mesh.receiveShadow = false;
            patch.add(mesh);
        }
        patch.userData.phase = random() * TAU;
        patches.push(patch);
    }
    return patches;
}

function addGrass(THREE, scene, seed, density) {
    const random = randomGenerator(seed);
    const grass = new THREE.Group();
    scene.add(grass);

    const geometry = new THREE.ConeGeometry(0.035, 0.26, 4, 1);
    const materials = ["#697a4c", "#82905c", "#5e7047"].map(color =>
        new THREE.MeshStandardMaterial({ color, roughness: 1 }),
    );
    const dummy = new THREE.Object3D();

    materials.forEach((material, materialIndex) => {
        const capacity = Math.round(280 * density);
        const mesh = new THREE.InstancedMesh(geometry, material, capacity);
        let count = 0;
        for (let index = 0; index < capacity; index += 1) {
            const x = (random() - 0.5) * 14;
            const z = (random() - 0.5) * 9.5;
            if (!insideTerrain(x, z, 0.2)) continue;
            const hiveClearance = [-3.1, 0, 3.1].some(hiveX =>
                Math.hypot(x - hiveX, z - 0.4) < 1.15,
            );
            if (hiveClearance) continue;
            dummy.position.set(x, terrainHeight(x, z) + 0.1, z);
            dummy.rotation.set(
                (random() - 0.5) * 0.28,
                random() * TAU,
                (random() - 0.5) * 0.28,
            );
            const height = 0.78 + random() * 0.88;
            dummy.scale.set(0.6 + random() * 0.5, height, 0.6 + random() * 0.5);
            dummy.updateMatrix();
            mesh.setMatrixAt(count++, dummy.matrix);
        }
        mesh.count = count;
        mesh.instanceMatrix.needsUpdate = true;
        mesh.castShadow = false;
        mesh.receiveShadow = false;
        grass.add(mesh);
    });
    grass.userData.phase = random() * TAU;
    return grass;
}

function addRocks(THREE, scene, random) {
    const rockMaterial = new THREE.MeshStandardMaterial({
        color: "#888574",
        roughness: 0.94,
        flatShading: true,
    });
    for (let index = 0; index < 14; index += 1) {
        const x = (random() - 0.5) * 13.5;
        const z = (random() - 0.5) * 9.1;
        if (!insideTerrain(x, z, 0.15)) continue;
        const rock = new THREE.Mesh(
            new THREE.DodecahedronGeometry(0.12 + random() * 0.18, 0),
            rockMaterial,
        );
        rock.position.set(x, terrainHeight(x, z) + 0.08, z);
        rock.rotation.set(random(), random() * TAU, random());
        rock.scale.set(1.2, 0.75 + random() * 0.45, 0.95);
        rock.castShadow = false;
        rock.receiveShadow = true;
        scene.add(rock);
    }
}

function addBees(THREE, scene) {
    const bees = [];
    const bodyMaterial = new THREE.MeshStandardMaterial({
        color: "#c79038",
        roughness: 0.6,
        metalness: 0.02,
    });
    const stripeMaterial = new THREE.MeshStandardMaterial({
        color: "#37291c",
        roughness: 0.7,
    });
    const wingMaterial = new THREE.MeshStandardMaterial({
        color: "#e9e5d6",
        roughness: 0.3,
        transparent: true,
        opacity: 0.72,
        side: THREE.DoubleSide,
    });
    const bodyGeometry = new THREE.SphereGeometry(0.1, 10, 7);
    const headGeometry = new THREE.SphereGeometry(0.055, 8, 6);
    const stripeGeometry = new THREE.TorusGeometry(0.072, 0.012, 5, 12);
    const wingGeometry = new THREE.SphereGeometry(0.07, 8, 5);

    for (let index = 0; index < 7; index += 1) {
        const bee = new THREE.Group();
        const abdomen = new THREE.Mesh(bodyGeometry, bodyMaterial);
        abdomen.scale.set(1.3, 0.78, 0.76);
        abdomen.castShadow = false;
        bee.add(abdomen);

        for (const x of [-0.015, 0.045]) {
            const stripe = new THREE.Mesh(stripeGeometry, stripeMaterial);
            stripe.rotation.y = Math.PI / 2;
            stripe.position.x = x;
            bee.add(stripe);
        }

        const head = new THREE.Mesh(headGeometry, stripeMaterial);
        head.position.x = 0.13;
        bee.add(head);

        const wings = new THREE.Group();
        for (const side of [-1, 1]) {
            const wing = new THREE.Mesh(wingGeometry, wingMaterial);
            wing.position.set(0.015, 0.055, side * 0.045);
            wing.scale.set(0.9, 0.28, 1.55);
            wings.add(wing);
        }
        bee.add(wings);
        bee.scale.setScalar(0.55 + (index % 3) * 0.08);
        scene.add(bee);
        bees.push({ group: bee, wings, phase: index * 1.71, radius: 0.8 + (index % 3) * 0.35 });
    }
    return bees;
}

function randomTerrainPoint(random, occupied, minimumDistance, margin = 1) {
    for (let attempt = 0; attempt < 160; attempt += 1) {
        const x = (random() - 0.5) * 12.5;
        const z = (random() - 0.5) * 8.5;
        if (!insideTerrain(x, z, margin)) continue;
        if (occupied.some(point => Math.hypot(x - point.x, z - point.z) < minimumDistance)) {
            continue;
        }
        return { x, z };
    }
    return { x: 0, z: 0 };
}

export function createDiorama(THREE, scene, zone) {
    const profile = zoneProfile(zone);
    const random = randomGenerator(zoneSeed(zone));
    const root = new THREE.Group();
    const groundTexture = makeGroundTexture(THREE, random);
    const woodTexture = makeWoodTexture(THREE, random);
    const groundMaterial = new THREE.MeshStandardMaterial({
        map: groundTexture,
        color: profile.groundColor,
        roughness: 1,
    });
    const woodMaterial = new THREE.MeshStandardMaterial({
        map: woodTexture,
        color: "#d0b080",
        roughness: 0.86,
    });
    const darkWood = new THREE.MeshStandardMaterial({
        color: "#664a2e",
        roughness: 0.9,
    });
    const roofMaterial = new THREE.MeshStandardMaterial({
        color: "#59634e",
        roughness: 0.74,
        metalness: 0.08,
    });
    const treeMaterials = {
        trunk: new THREE.MeshStandardMaterial({ color: "#6b5034", roughness: 0.95 }),
        leaves: profile.leafColors.map(color =>
            new THREE.MeshStandardMaterial({ color, roughness: 0.96 }),
        ),
    };

    addTerrain(THREE, root, groundMaterial);

    const hivePositions = [
        { x: -3.2, z: 0.35 },
        { x: 0, z: -0.15 },
        { x: 3.25, z: 0.5 },
    ];
    const hives = [
        addHive(THREE, root, -3.2, 0.35, 0.92, woodMaterial, darkWood, roofMaterial, 1),
        addHive(THREE, root, 0, -0.15, 1.05, woodMaterial, darkWood, roofMaterial, 2),
        addHive(THREE, root, 3.25, 0.5, 0.88, woodMaterial, darkWood, roofMaterial, 3),
    ];

    const occupied = [...hivePositions];
    const trees = [];
    for (let index = 0; index < profile.trees; index += 1) {
        const position = randomTerrainPoint(random, occupied, 2.1, 1.5);
        occupied.push(position);
        trees.push(addTree(
            THREE,
            root,
            position.x,
            position.z,
            0.78 + random() * 0.28,
            treeMaterials,
            random() * 4294967296,
            profile.treeStyle,
        ));
    }
    const bushes = [];
    for (let index = 0; index < profile.bushes; index += 1) {
        const position = randomTerrainPoint(random, occupied, 1.35, 0.6);
        occupied.push(position);
        bushes.push(addBush(
            THREE,
            root,
            position.x,
            position.z,
            0.62 + random() * 0.34,
            treeMaterials,
            random() * 4294967296,
        ));
    }

    const flowerPatches = addFlowers(THREE, root, random() * 4294967296, profile);
    const grass = addGrass(THREE, root, random() * 4294967296, profile.grassDensity);
    addRocks(THREE, root, random);
    const bees = addBees(THREE, root);
    root.scale.set(profile.surfaceScale, 1, profile.surfaceScale);
    root.userData.zoneId = zone?.id ?? null;
    scene.add(root);

    return {
        root,
        hives,
        trees,
        bushes,
        flowerPatches,
        grass,
        bees,
        groundMaterial,
        profile,
        groundTexture,
        woodTexture,
    };
}

export { terrainHeight };
