/* =========================================
   RICOZ ASSISTANT
   SIMPLE CUSTOMER CHATBOT
========================================= */

const chatForm = document.getElementById("chatForm");
const chatInput = document.getElementById("chatInput");
const chatMessages = document.getElementById("chatMessages");


function addMessage(message, type = "assistant") {

    const messageWrapper = document.createElement("div");

    if (type === "user") {

        messageWrapper.className = "message user-message";

        messageWrapper.style.alignSelf = "flex-end";
        messageWrapper.style.justifyContent = "flex-end";

        messageWrapper.innerHTML = `
            <div class="message-content">
                <span class="message-name" style="text-align:right;">
                    You
                </span>

                <p style="
                    background:#e31e24;
                    color:#ffffff;
                    border:none;
                    border-radius:13px 4px 13px 13px;
                ">
                    ${escapeHtml(message)}
                </p>
            </div>
        `;

    } else {

        messageWrapper.className = "message assistant-message";

        messageWrapper.innerHTML = `
            <div class="message-avatar">
                R
            </div>

            <div class="message-content">
                <span class="message-name">
                    Ricoz Assistant
                </span>

                <p>
                    ${message}
                </p>
            </div>
        `;
    }

    chatMessages.appendChild(messageWrapper);

    chatMessages.scrollTop = chatMessages.scrollHeight;
}


function escapeHtml(text) {

    const div = document.createElement("div");

    div.textContent = text;

    return div.innerHTML;
}


function getBotResponse(message) {

    const text = message.toLowerCase();


    if (
        text.includes("hello") ||
        text.includes("hi") ||
        text.includes("hey")
    ) {
        return `
            Hello! 👋 How can I help you with your Ricoz account?
        `;
    }


    if (
        text.includes("account") ||
        text.includes("profile")
    ) {
        return `
            You can manage your account information from the
            <strong>My Account</strong> section.
        `;
    }


    if (
        text.includes("subscription") ||
        text.includes("plan")
    ) {
        return `
            You can view your current subscription and plan
            information from the <strong>Subscription</strong>
            section.
        `;
    }


    if (
        text.includes("billing") ||
        text.includes("invoice") ||
        text.includes("payment")
    ) {
        return `
            Your invoices and billing information are available
            in the <strong>Billing</strong> section.
        `;
    }


    if (
        text.includes("support") ||
        text.includes("help") ||
        text.includes("problem")
    ) {
        return `
            You can contact our support team through the
            <strong>Support</strong> section. You can also
            create a support ticket there.
        `;
    }


    if (
        text.includes("password") ||
        text.includes("security")
    ) {
        return `
            You can change your password and manage security
            options from the <strong>Settings</strong> section.
        `;
    }


    if (
        text.includes("thank") ||
        text.includes("thanks")
    ) {
        return `
            You're welcome! 😊 Let me know if you need anything else.
        `;
    }


    return `
        I'm here to help with your Ricoz account, subscription,
        billing, support and settings.

        <br><br>

        You can also choose one of the quick questions below.
    `;
}


function sendMessage(message) {

    if (!message || !message.trim()) {
        return;
    }

    addMessage(message, "user");

    chatInput.value = "";

    setTimeout(() => {

        const response = getBotResponse(message);

        addMessage(response, "assistant");

    }, 450);
}


function sendQuickMessage(message) {

    sendMessage(message);
}


chatForm.addEventListener("submit", function(event) {

    event.preventDefault();

    sendMessage(chatInput.value);

});


chatInput.addEventListener("keydown", function(event) {

    if (event.key === "Enter") {

        event.preventDefault();

        sendMessage(chatInput.value);
    }

});