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

    // --- Filtros recolhíveis no celular ---
    if (window.matchMedia("(max-width: 760px)").matches) {
        document.querySelectorAll("details[data-collapse-mobile='true']").forEach(function (details) {
            details.open = false;
        });
    }

    // --- Pré-visualização de imagens antes do envio ---
    // Só melhora a experiência (o servidor valida tudo de novo): mostra as
    // miniaturas escolhidas e avisa se passar do limite de fotos ou de 5 MB.
    document.querySelectorAll("input[data-image-input]").forEach(function (input) {
        const preview = document.getElementById(input.dataset.preview);
        const maxFiles = parseInt(input.dataset.maxFiles, 10);
        const maxBytes = 5 * 1024 * 1024;

        input.addEventListener("change", function () {
            preview.innerHTML = "";
            const files = Array.from(input.files);
            const problems = [];

            if (files.length > maxFiles) {
                problems.push(maxFiles > 0
                    ? "Você pode adicionar no máximo " + maxFiles + " foto(s)."
                    : "Esta tarefa já tem 3 fotos. Remova alguma para adicionar outra.");
            }
            files.forEach(function (file) {
                if (file.size > maxBytes) {
                    problems.push('"' + file.name + '" tem mais de 5 MB.');
                }
            });

            if (problems.length) {
                const warning = document.createElement("p");
                warning.className = "image-preview-error";
                warning.textContent = problems.join(" ");
                preview.appendChild(warning);
                input.value = "";
                return;
            }

            files.forEach(function (file) {
                const img = document.createElement("img");
                img.src = URL.createObjectURL(file);
                img.alt = "Pré-visualização de " + file.name;
                img.onload = function () { URL.revokeObjectURL(img.src); };
                preview.appendChild(img);
            });
        });
    });
});
