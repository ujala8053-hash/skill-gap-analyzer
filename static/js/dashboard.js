document.addEventListener("DOMContentLoaded", () => {
    const chatForm = document.getElementById("strategy-chat-form");
    const chatInput = document.getElementById("strategy-message");
    const chatLog = document.getElementById("strategy-chat-log");
    const status = document.getElementById("strategy-chat-status");
    const roleInput = document.getElementById("role");
    const skillsInput = document.getElementById("skills");
    const promptButtons = document.querySelectorAll("[data-strategy-prompt]");
    const promptList = document.querySelector(".coach-prompts");
    const summaryMatch = document.getElementById("strategy-match");
    const summaryPriority = document.getElementById("strategy-priority");
    const summaryCourse = document.getElementById("strategy-course");
    let isSubmitting = false;

    if (!chatForm || !chatInput || !chatLog) {
        return;
    }

    function appendMessage(type, label, content) {
        const wrapper = document.createElement("div");
        wrapper.className = `chat-message ${type}`;

        const meta = document.createElement("div");
        meta.className = "chat-meta";
        meta.textContent = label;

        const body = document.createElement("div");
        body.textContent = content;

        wrapper.appendChild(meta);
        wrapper.appendChild(body);
        chatLog.appendChild(wrapper);
        chatLog.scrollTop = chatLog.scrollHeight;

        return wrapper;
    }

    function setStatus(message) {
        if (status) {
            status.textContent = message;
        }
    }

    function updateSummary(summary) {
        if (!summary) {
            return;
        }

        if (summaryMatch) {
            summaryMatch.textContent = `${Number(summary.match || 0)}%`;
        }
        if (summaryPriority) {
            const skills = Array.isArray(summary.priority_skills) ? summary.priority_skills : [];
            summaryPriority.textContent = skills.length ? skills.join(", ") : "Add a role and skills";
        }
        if (summaryCourse) {
            summaryCourse.textContent = summary.recommended_course || "Add a role to get a course recommendation";
        }
    }

    function wirePromptButton(button) {
        button.addEventListener("click", () => {
            const prompt = button.getAttribute("data-strategy-prompt");
            if (!prompt) {
                return;
            }
            chatInput.value = prompt;
            submitStrategyMessage(prompt);
        });
    }

    function updatePromptChips(prompts) {
        if (!promptList || !Array.isArray(prompts) || !prompts.length) {
            return;
        }

        promptList.innerHTML = "";

        prompts.forEach((prompt) => {
            const button = document.createElement("button");
            button.type = "button";
            button.className = "prompt-chip";
            button.setAttribute("data-strategy-prompt", prompt);
            button.textContent = prompt;
            wirePromptButton(button);
            promptList.appendChild(button);
        });
    }

    async function submitStrategyMessage(message) {
        const trimmed = String(message || "").trim();
        if (!trimmed || isSubmitting) {
            return;
        }

        isSubmitting = true;
        appendMessage("user", "You", trimmed);
        chatInput.value = "";
        setStatus("Strategy coach is preparing a response...");

        const typingMessage = appendMessage("assistant", "Coach", "Thinking through your next best move...");

        try {
            const response = await fetch("/strategy_chat", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    message: trimmed,
                    role: roleInput ? roleInput.value : "",
                    skills: skillsInput ? skillsInput.value : "",
                }),
            });

            const payload = await response.json();
            typingMessage.remove();

            if (!response.ok) {
                appendMessage("assistant", "Coach", payload.error || "I ran into an issue while building that strategy response.");
                setStatus("Please revise your message and try again.");
                return;
            }

            appendMessage("assistant", "Coach", payload.reply);
            updateSummary(payload.summary);
            updatePromptChips(payload.follow_up_prompts);
            setStatus("Ask another question to refine the plan.");
        } catch (error) {
            typingMessage.remove();
            appendMessage("assistant", "Coach", "The chat request failed. Please try again in a moment.");
            setStatus("Connection issue while loading the strategy response.");
        } finally {
            isSubmitting = false;
        }
    }

    chatForm.addEventListener("submit", (event) => {
        event.preventDefault();
        submitStrategyMessage(chatInput.value);
    });

    promptButtons.forEach(wirePromptButton);
});
