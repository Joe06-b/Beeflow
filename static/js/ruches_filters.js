(() => {
  "use strict";

  document.querySelectorAll("[data-ruches-filters]").forEach((form) => {
    form.querySelectorAll("[data-ruches-filter]").forEach((select) => {
      select.addEventListener("change", () => {
        if (typeof form.requestSubmit === "function") form.requestSubmit();
        else form.submit();
      });
    });
  });
})();
