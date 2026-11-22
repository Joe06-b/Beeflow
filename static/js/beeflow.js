document.addEventListener("DOMContentLoaded", () => {

    // Date automatique (backoffice)
    const dateElement = document.getElementById("currentDate");
    if (dateElement) {
        dateElement.textContent = new Date().toLocaleDateString("fr-FR", {
            weekday: "long", day: "numeric", month: "long", year: "numeric"
        });
    }

    // Compteurs animés
    document.querySelectorAll(".counter").forEach(counter => {
        const target = Number(counter.dataset.target);
        let current = 0;
        const increment = Math.max(1, Math.ceil(target / 50));

        const timer = setInterval(() => {
            current += increment;
            if (current >= target) {
                current = target;
                clearInterval(timer);
            }
            counter.textContent = current;
        }, 30);
    });

    // Animation des barres du graphique
    document.querySelectorAll(".bar").forEach((bar, index) => {
        setTimeout(() => { bar.style.height = bar.dataset.height; }, index * 120);
    });

    // Menu mobile
    const sidebar = document.getElementById("sidebar");
    document.querySelectorAll("[data-toggle-menu]").forEach(btn => {
        btn.addEventListener("click", () => sidebar && sidebar.classList.toggle("open"));
    });

    // Modules pas encore développés : lien avec l'attribut data-soon
    document.querySelectorAll("a[data-soon]").forEach(link => {
        link.addEventListener("click", event => {
            event.preventDefault();
            const title = link.textContent.trim();
            alert("Le module « " + title + " » sera disponible dans la prochaine étape.");
            if (sidebar && window.innerWidth <= 650) sidebar.classList.remove("open");
        });
    });

});
