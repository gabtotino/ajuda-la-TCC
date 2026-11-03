// static/js/main.js
// JavaScript compartilhado por todas as páginas.

document.addEventListener("DOMContentLoaded", function () {
    // --- Menu hambúrguer (celular) ---
    // Abaixo de 760px o menu fica escondido e o botão alterna a classe
    // "nav-open" no header; aria-expanded mantém leitores de tela informados.
    const header = document.querySelector(".site-header");
    const toggle = document.querySelector(".nav-toggle");
    if (header && toggle) {
        toggle.addEventListener("click", function () {
            const isOpen = header.classList.toggle("nav-open");
            toggle.setAttribute("aria-expanded", String(isOpen));
            toggle.setAttribute("aria-label", isOpen ? "Fechar menu" : "Abrir menu");
        });

        document.addEventListener("keydown", function (event) {
            if (event.key === "Escape" && header.classList.contains("nav-open")) {
                header.classList.remove("nav-open");
                toggle.setAttribute("aria-expanded", "false");
                toggle.focus();
            }
        });
    }

    // --- Confirmação de ações destrutivas ---
    // Qualquer <form data-confirm="..."> pede confirmação antes de enviar,
    // sem precisar de onsubmit inline em cada template.
    document.querySelectorAll("form[data-confirm]").forEach(function (form) {
        form.addEventListener("submit", function (event) {
            if (!window.confirm(form.dataset.confirm)) {
                event.preventDefault();
            }
        });
    });

    // --- Contador de caracteres ---
    // <textarea data-maxlength-counter="id-do-contador" maxlength="500">
    document.querySelectorAll("[data-maxlength-counter]").forEach(function (field) {
        const counter = document.getElementById(field.dataset.maxlengthCounter);
        if (!counter) {
            return;
        }
        const update = function () {
            counter.textContent = field.value.length + "/" + field.maxLength;
        };
        field.addEventListener("input", update);
        update();
    });
});
