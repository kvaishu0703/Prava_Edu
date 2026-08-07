document.addEventListener("DOMContentLoaded", () => {
    document.body.dataset.appReady = "true";

    document.querySelectorAll("[data-print-page]").forEach((button) => {
        button.addEventListener("click", () => window.print());
    });
});
