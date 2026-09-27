let sessionId = localStorage.getItem("session_id");
if (!sessionId) {
    sessionId = "session_" + Date.now() + "_" + Math.floor(Math.random() * 100000);
    localStorage.setItem("session_id", sessionId);
}

const BACKEND_URL = "http://32.192.50.98:8000";
let lastQuestion = null;

const chatButton = document.getElementById("openChatBtn");
const chatWindow = document.getElementById("chatWindow");
const sendBtn = document.getElementById("sendBtn");
const userInput = document.getElementById("userInput");
const chatMessages = document.getElementById("chatMessages");

chatButton.addEventListener("click", openChatbot);

function openChatbot() {
    chatWindow.style.display = "flex";
    userInput.focus();
}

function closeChatbot() {
    chatWindow.style.display = "none";
    if (lastQuestion !== null) {
        document.getElementById("feedbackModal").style.display = "flex";
    }
}

document.querySelectorAll('.card').forEach(card => {
    card.addEventListener('click', () => {
        const serviceName = card.innerText.trim();
        openChatbot();
        userInput.value = `How do I apply for ${serviceName}?`;
        sendMessage();
    });
});

sendBtn.addEventListener("click", sendMessage);
userInput.addEventListener("keypress", function (e) {
    if (e.key === "Enter") sendMessage();
});

async function sendMessage() {
    const question = userInput.value.trim();
    if (!question) return;

    displayMessage("user", question);
    userInput.value = "";
    chatMessages.scrollTop = chatMessages.scrollHeight;
    const typingId = showTypingIndicator();

    try {
        const response = await fetch(`${BACKEND_URL}/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ session_id: sessionId, question: question, previous_question: lastQuestion })
        });

        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        removeTypingIndicator(typingId);
        
        displayMessage("bot", data.answer);

        if (data.follow_ups && Array.isArray(data.follow_ups) && data.follow_ups.length > 0) {
            displayFollowUps(data.follow_ups);
        }
        lastQuestion = question;

    } catch (error) {
        console.error("Error:", error);
        removeTypingIndicator(typingId);
        displayMessage("bot", "Sorry, I couldn't connect to the server. Please try again.", "error-message");
    }
}

function displayMessage(sender, message, type = "") {
    const messageElement = document.createElement("div");
    messageElement.className = `message ${sender}-message ${type}`.trim();
    if (sender === "bot") {
        messageElement.innerHTML = marked.parse(message);
    } else {
        const textNode = document.createTextNode(message);
        messageElement.appendChild(textNode);
    }
    chatMessages.appendChild(messageElement);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function displayFollowUps(questions) {
    const followUpContainer = document.createElement("div");
    followUpContainer.style.display = "flex";
    followUpContainer.style.flexWrap = "wrap";
    followUpContainer.style.gap = "8px";
    followUpContainer.style.marginTop = "10px";
    followUpContainer.style.marginBottom = "15px";

    questions.forEach(q => {
        const btn = document.createElement("button");
        btn.textContent = q;
        btn.style.padding = "8px 12px";
        btn.style.borderRadius = "20px";
        btn.style.border = "1px solid #00695c";
        btn.style.background = "white";
        btn.style.color = "#00695c";
        btn.style.cursor = "pointer";
        btn.style.fontSize = "13px";
        btn.style.transition = "0.2s";

        btn.onmouseover = () => { btn.style.background = "#e6f0ef"; };
        btn.onmouseout = () => { btn.style.background = "white"; };
        btn.addEventListener("click", () => {
            userInput.value = q;
            sendMessage();
            followUpContainer.remove(); 
        });
        followUpContainer.appendChild(btn);
    });
    chatMessages.appendChild(followUpContainer);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function showTypingIndicator() {
    const typingElement = document.createElement("div");
    typingElement.className = "message bot-message typing";
    typingElement.id = "typing-indicator";
    typingElement.innerHTML = '<span>.</span><span>.</span><span>.</span>';
    chatMessages.appendChild(typingElement);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return "typing-indicator";
}

function removeTypingIndicator(id) {
    const element = document.getElementById(id);
    if (element) element.remove();
}

// FEEDBACK LOGIC
const feedbackModal = document.getElementById("feedbackModal");
const stars = document.querySelectorAll(".stars span");
let selectedRating = 0;

stars.forEach(star => {
    star.addEventListener("click", (e) => {
        selectedRating = parseInt(e.target.getAttribute("data-value"));
        stars.forEach((s, index) => {
            if (index < selectedRating) s.classList.add("active");
            else s.classList.remove("active");
        });
    });
});

document.getElementById("skipFeedback").addEventListener("click", () => {
    feedbackModal.style.display = "none";
    lastQuestion = null;
    resetFeedbackForm();
});

document.getElementById("submitFeedback").addEventListener("click", async () => {
    if (selectedRating === 0) {
        alert("Please select a star rating first!");
        return;
    }
    const comments = document.getElementById("feedbackText").value;
    const queryId = "query_" + Date.now(); 

    try {
        await fetch(`${BACKEND_URL}/feedback`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ query_id: queryId, session_id: sessionId, rating: selectedRating, feedback: comments })
        });
        feedbackModal.style.display = "none";
        lastQuestion = null;
        resetFeedbackForm();
        alert("Thank you for your feedback! It helps us improve.");
    } catch (error) {
        console.error("Error submitting feedback:", error);
        alert("Something went wrong, but thank you anyway!");
        feedbackModal.style.display = "none";
    }
});

function resetFeedbackForm() {
    selectedRating = 0;
    stars.forEach(s => s.classList.remove("active"));
    document.getElementById("feedbackText").value = "";
}