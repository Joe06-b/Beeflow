(() => {
  "use strict";

  const clamp = (value, min, max) => Math.min(max, Math.max(min, value));

  document.querySelectorAll("[data-hive-3d]").forEach((viewer) => {
    const model = viewer.querySelector("[data-hive-3d-shell]");
    if (!model) return;

    let rotateX = -4;
    let rotateY = -12;
    let startX = 0;
    let startY = 0;
    let startRotateX = rotateX;
    let startRotateY = rotateY;
    let activePointer = null;

    const render = () => {
      model.style.setProperty("--hive-rotate-x", `${rotateX}deg`);
      model.style.setProperty("--hive-rotate-y", `${rotateY}deg`);
      model.style.setProperty("--hive-light-x", `${Math.min(78, Math.max(22, 50 - rotateY * 0.45))}%`);
    };

    const reset = () => {
      rotateX = -4;
      rotateY = -12;
      render();
    };

    viewer.addEventListener("pointerdown", (event) => {
      if (event.button !== 0) return;
      activePointer = event.pointerId;
      startX = event.clientX;
      startY = event.clientY;
      startRotateX = rotateX;
      startRotateY = rotateY;
      viewer.classList.add("is-dragging");
      viewer.setPointerCapture(event.pointerId);
    });

    viewer.addEventListener("pointermove", (event) => {
      if (event.pointerId !== activePointer) return;
      rotateY = startRotateY + (event.clientX - startX) * 0.65;
      rotateX = clamp(startRotateX - (event.clientY - startY) * 0.4, -38, 38);
      render();
      event.preventDefault();
    });

    const stopDragging = (event) => {
      if (event.pointerId !== activePointer) return;
      viewer.classList.remove("is-dragging");
      if (viewer.hasPointerCapture(event.pointerId)) viewer.releasePointerCapture(event.pointerId);
      activePointer = null;
    };

    viewer.addEventListener("pointerup", stopDragging);
    viewer.addEventListener("pointercancel", stopDragging);
    viewer.addEventListener("dblclick", reset);

    viewer.addEventListener("keydown", (event) => {
      const step = event.shiftKey ? 20 : 8;
      if (event.key === "ArrowLeft") rotateY -= step;
      else if (event.key === "ArrowRight") rotateY += step;
      else if (event.key === "ArrowUp") rotateX = clamp(rotateX - step, -38, 38);
      else if (event.key === "ArrowDown") rotateX = clamp(rotateX + step, -38, 38);
      else if (event.key === "Home") reset();
      else return;
      render();
      event.preventDefault();
    });

    render();
  });
})();
