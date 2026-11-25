import { terrainHeight } from "./diorama.js";

export function createNaturalAnimations(diorama) {
    let elapsed = 0;
    let wind = 0;
    let targetWind = 0;
    let daylight = 0;
    let targetDaylight = 0;
    let windDirection = 0;
    let wetness = 0;
    let targetWetness = 0;
    diorama.bees.forEach(bee => {
        bee.group.visible = false;
    });

    return {
        setWeather(state) {
            targetWind = state.active && Number.isFinite(state.windSpeed)
                ? Math.min(1, Math.max(0, state.windSpeed / 55))
                : 0;
            targetDaylight = state.active
                && Number.isFinite(state.daylightFactor)
                ? Math.min(1, Math.max(0, state.daylightFactor))
                : state.active && typeof state.isNight === "boolean"
                    ? (state.isNight ? 0 : 1)
                    : 0;
            windDirection = Number.isFinite(state.windDirectionDegrees)
                ? ((state.windDirectionDegrees + 180) % 360) * Math.PI / 180
                : 0;
            const precipitation = Math.max(
                Number.isFinite(state.rain) ? state.rain : 0,
                Number.isFinite(state.precipitation) ? state.precipitation : 0,
            );
            targetWetness = state.active && precipitation > 0
                ? Math.min(1, Math.sqrt(precipitation) / 3)
                : 0;
        },

        update(delta, snap = false) {
            elapsed += delta;
            const blend = snap ? 1 : 1 - Math.exp(-delta * 1.5);
            wind += (targetWind - wind) * blend;
            daylight += (targetDaylight - daylight) * blend;
            wetness += (targetWetness - wetness) * blend;
            if (diorama.groundMaterial) {
                diorama.groundMaterial.roughness = 1 - wetness * 0.52;
            }
            const sway = wind * 0.045;
            const windX = Math.sin(windDirection) * sway;
            const windZ = Math.cos(windDirection) * sway;

            diorama.trees.forEach((tree, index) => {
                const phase = elapsed * (0.32 + wind * 0.55) + index * 1.7;
                tree.rotation.z = tree.userData.baseRotation + Math.sin(phase) * windX;
                tree.rotation.x = Math.cos(phase * 0.74) * windZ * 0.55;
            });
            diorama.bushes.forEach((bush, index) => {
                const phase = elapsed * 0.62 + index * 2.2;
                bush.rotation.z = Math.sin(phase) * windX * 0.42;
                bush.rotation.x = Math.cos(phase * 0.8) * windZ * 0.3;
            });
            diorama.flowerPatches.forEach((patch, index) => {
                const phase = elapsed * (0.78 + wind * 0.7) + patch.userData.phase;
                patch.rotation.z = Math.sin(phase) * windX * 1.25;
                patch.rotation.x = Math.cos(phase * 0.8 + index) * windZ * 0.7;
            });
            diorama.grass.rotation.z = Math.sin(
                elapsed * 0.65 + diorama.grass.userData.phase,
            ) * windX * 0.22;
            diorama.grass.rotation.x = Math.cos(
                elapsed * 0.58 + diorama.grass.userData.phase,
            ) * windZ * 0.16;

            diorama.bees.forEach((bee, index) => {
                const phase = elapsed * (0.75 + index * 0.035) + bee.phase;
                const hiveIndex = index % diorama.hives.length;
                const hive = diorama.hives[hiveIndex];
                const centerX = hive.position.x;
                const centerZ = hive.position.z + 0.8;
                const radius = bee.radius;
                const activity = daylight;
                bee.group.position.set(
                    centerX + Math.cos(phase) * radius * activity,
                    terrainHeight(centerX, centerZ) + 2.05 + Math.sin(phase * 2.1) * 0.2 * activity,
                    centerZ + Math.sin(phase) * radius * activity,
                );
                bee.group.rotation.y = -phase + Math.PI / 2;
                bee.wings.rotation.x = Math.sin(elapsed * 24 + index) * 0.33;
                bee.group.visible = activity > 0.2;
            });
        },
    };
}
