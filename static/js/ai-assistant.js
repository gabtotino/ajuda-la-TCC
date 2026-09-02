// static/js/ai-assistant.js
// Liga o botão "Interpretar com IA" do formulário de criação de tarefa:
// envia o texto livre digitado pelo usuário para /ai/interpretar-tarefa e,
// se a IA responder com sucesso, pré-preenche os campos do formulário.
// Se a chamada falhar por qualquer motivo (sem chave configurada, API fora
// do ar, resposta inválida...), mostra um aviso e o usuário simplesmente
// preenche o formulário manualmente — esse fallback é um requisito da
// funcionalidade, não um detalhe de implementação.
document.addEventListener("DOMContentLoaded", function () {
    const button = document.getElementById("ai-assist-button");
    if (!button) {
        return;
    }

    const textarea = document.getElementById("ai-assist-text");
    const statusEl = document.getElementById("ai-assist-status");
    const csrfInput = document.querySelector('input[name="csrf_token"]');

    button.addEventListener("click", function () {
        const text = textarea.value.trim();
        if (!text) {
            statusEl.textContent = "Descreva a tarefa no campo acima antes de interpretar.";
            return;
        }

        button.disabled = true;
        statusEl.textContent = "Interpretando com IA...";

        fetch("/ai/interpretar-tarefa", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text: text, csrf_token: csrfInput.value }),
        })
            .then(function (response) {
                return response.json();
            })
            .then(function (payload) {
                if (!payload.success) {
                    statusEl.textContent = payload.message || "Não foi possível interpretar o texto. Preencha manualmente.";
                    return;
                }

                const data = payload.data;
                document.getElementById("title").value = data.titulo || "";
                document.getElementById("description").value = data.descricao || "";

                if (data.valor_sugerido !== null && data.valor_sugerido !== undefined) {
                    document.getElementById("value").value = String(data.valor_sugerido).replace(".", ",");
                }

                const categorySelect = document.getElementById("category");
                if (data.categoria && categorySelect) {
                    categorySelect.value = data.categoria;
                }

                statusEl.textContent = "Campos preenchidos! Revise antes de publicar.";
            })
            .catch(function () {
                statusEl.textContent = "Erro de conexão com a IA. Preencha manualmente.";
            })
            .finally(function () {
                button.disabled = false;
            });
    });
});
