document.addEventListener("DOMContentLoaded", () => {
    document.body.dataset.appReady = "true";
    document.querySelectorAll("[data-print-page]").forEach(button => button.addEventListener("click", () => window.print()));
    document.querySelectorAll("[data-menu-toggle], [data-sidebar-toggle]").forEach(button => {
        button.addEventListener("click", () => {
            const expanded = button.getAttribute("aria-expanded") === "true";
            button.setAttribute("aria-expanded", String(!expanded));
            const panel = document.getElementById(button.getAttribute("aria-controls"));
            panel.classList.toggle("is-open", !expanded);
            if (expanded) panel.querySelectorAll("[data-login-dropdown]").forEach(dropdown => { dropdown.open = false; });
        });
    });
    document.querySelectorAll("[data-login-dropdown]").forEach(dropdown => {
        const trigger = dropdown.querySelector("summary");
        document.addEventListener("click", event => {
            if (!dropdown.contains(event.target)) dropdown.open = false;
        });
        document.addEventListener("keydown", event => {
            if (event.key === "Escape" && dropdown.open) {
                dropdown.open = false;
                trigger.focus();
                event.preventDefault();
            }
        });
        dropdown.addEventListener("focusout", event => {
            if (!dropdown.contains(event.relatedTarget)) dropdown.open = false;
        });
    });
    document.querySelectorAll("[data-password-toggle]").forEach(button => {
        button.addEventListener("click", () => {
            const input = button.closest(".password-field").querySelector("input");
            const show = input.type === "password";
            input.type = show ? "text" : "password";
            button.setAttribute("aria-label", show ? "Hide password" : "Show password");
            button.setAttribute("aria-pressed", String(show));
            button.querySelector("i").className = show ? "bi bi-eye-slash" : "bi bi-eye";
        });
    });
});
