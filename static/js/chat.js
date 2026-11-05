// static/js/chat.js
// Chat da tarefa: envia mensagens via fetch (JSON) e busca as novas a cada
// 5 segundos (polling). Todo texto vindo do servidor é inserido com
// textContent (nunca innerHTML), então uma mensagem com "<script>" aparece
// como texto e não é executada (proteção contra XSS).
document.addEventListener("DOMContentLoaded", function () {
    const box = document.querySelector("[data-chat]");
    if (!box) {
        return;
    }

    const apiUrl = box.dataset.apiUrl;
    const csrfToken = box.dataset.csrf;
    const list = document.getElementById("chat-messages");
    const form = document.getElementById("chat-form");
    const input = document.getElementById("chat-input");
    const errorEl = document.getElementById("chat-error");
    const POLL_INTERVAL_MS = 5000;

    function lastMessageId() {
        const bubbles = list.querySelectorAll("[data-id]");
        return bubbles.length ? parseInt(bubbles[bubbles.length - 1].dataset.id, 10) : 0;
    }

    function scrollToBottom() {
        list.scrollTop = list.scrollHeight;
    }

    function appendMessage(message) {
        // Evita duplicar se a mesma mensagem chegar pelo envio e pelo polling.
        if (list.querySelector('[data-id="' + message.id + '"]')) {
            return;
        }
        const empty = document.getElementById("chat-empty");
        if (empty) {
            empty.remove();
        }

        const bubble = document.createElement("div");
        bubble.className = "chat-bubble " + (message.mine ? "chat-bubble-mine" : "chat-bubble-theirs");
        bubble.dataset.id = message.id;

        const text = document.createElement("p");
        text.textContent = message.content;
        const time = document.createElement("span");
        time.className = "chat-time";
        time.textContent = message.time;

        bubble.appendChild(text);
        bubble.appendChild(time);
        list.appendChild(bubble);
    }

    function poll() {
        fetch(apiUrl + "?depois_de=" + lastMessageId(), { headers: { Accept: "application/json" } })
            .then(function (response) {
                return response.ok ? response.json() : null;
            })
            .then(function (data) {
                if (!data) {
                    return;
                }
                const nearBottom = list.scrollHeight - list.scrollTop - list.clientHeight < 80;
                data.messages.forEach(appendMessage);
                if (data.messages.length && nearBottom) {
                    scrollToBottom();
                }
                if (!data.chat_open && form) {
                    // A tarefa foi concluída enquanto a página estava aberta.
                    form.remove();
                }
            })
            .catch(function () {
                // Falha de rede momentânea: tenta de novo no próximo ciclo.
            });
    }

    if (form) {
        form.addEventListener("submit", function (event) {
            event.preventDefault();
            const content = input.value.trim();
            if (!content) {
                return;
            }
            const button = form.querySelector("button");
            button.disabled = true;
            errorEl.textContent = "";

            fetch(apiUrl, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ content: content, csrf_token: csrfToken }),
            })
                .then(function (response) {
                    return response.json().then(function (data) {
                        return { ok: response.ok, data: data };
                    });
                })
                .then(function (result) {
                    if (!result.ok) {
                        errorEl.textContent = result.data.error || "Não foi possível enviar.";
                        return;
                    }
                    appendMessage(result.data.message);
                    input.value = "";
                    scrollToBottom();
                })
                .catch(function () {
                    errorEl.textContent = "Sem conexão. Tente enviar de novo.";
                })
                .finally(function () {
                    button.disabled = false;
                    input.focus();
                });
        });
    }

    scrollToBottom();
    // Pausa o polling quando a aba não está visível (economiza requisições).
    setInterval(function () {
        if (!document.hidden) {
            poll();
        }
    }, POLL_INTERVAL_MS);
});
