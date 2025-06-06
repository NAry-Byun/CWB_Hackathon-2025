// Flask Backend Compatible AI Chat Interface with Speech-to-Text
console.log("🚀 Flask Compatible AI Chat with Speech-to-Text Started");

// Global variables
let isTyping = false;
let isListening = false;
let recognition = null;
let uploadedDocuments = [];
const BACKEND_URL = "http://127.0.0.1:5000"; // Flask backend

// DOM elements
let chatInput, chatMessages, submitBtn, typingIndicator, micBtn, speechStatus;

// Initialize when DOM loads
document.addEventListener("DOMContentLoaded", function () {
    console.log("🤖 AI Assistant with Speech-to-Text Initializing...");

    // Get DOM elements
    chatInput = document.getElementById("chatInput");
    chatMessages = document.getElementById("chatMessages");
    submitBtn = document.getElementById("submitBtn");
    typingIndicator = document.getElementById("typingIndicator");
    micBtn = document.getElementById("micBtn");
    speechStatus = document.getElementById("speechStatus");

    if (!chatInput || !chatMessages || !submitBtn || !micBtn) {
        console.error("❌ Essential DOM elements not found");
        return;
    }

    chatInput.focus();
    setupEventListeners();
    setupSpeechRecognition();
    addDocumentUploadUI();
    showWelcomeMessage();
    checkFlaskConnection();
});

// Setup Speech Recognition
function setupSpeechRecognition() {
    // Check browser support
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
        console.warn("⚠️ Speech Recognition not supported in this browser");
        micBtn.disabled = true;
        micBtn.title = "Speech Recognition not supported";
        micBtn.style.opacity = "0.3";
        return;
    }

    // Initialize Speech Recognition
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SpeechRecognition();

    // Configuration
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = 'en-US';
    recognition.maxAlternatives = 1;

    // Event handlers
    recognition.onstart = function() {
        console.log("🎤 Speech recognition started");
        isListening = true;
        updateMicButton();
        showSpeechStatus("🎤 Listening... Speak now!", "listening");
        chatInput.classList.add("listening");
        chatInput.placeholder = "Listening... Speak your message";
    };

    recognition.onresult = function(event) {
        let interimTranscript = '';
        let finalTranscript = '';

        for (let i = event.resultIndex; i < event.results.length; i++) {
            const transcript = event.results[i][0].transcript;
            if (event.results[i].isFinal) {
                finalTranscript += transcript;
            } else {
                interimTranscript += transcript;
            }
        }

        // Update input field with interim results
        if (interimTranscript) {
            chatInput.value = finalTranscript + interimTranscript;
            showSpeechStatus("🎤 " + interimTranscript, "listening");
        }

        // Handle final result
        if (finalTranscript) {
            chatInput.value = finalTranscript.trim();
            showSpeechStatus("✅ Speech captured!", "success");
            autoResizeTextarea(chatInput);
            toggleSubmitButton();
            
            setTimeout(() => {
                hideSpeechStatus();
            }, 2000);
        }
    };

    recognition.onerror = function(event) {
        console.error("❌ Speech recognition error:", event.error);
        isListening = false;
        updateMicButton();
        chatInput.classList.remove("listening");
        chatInput.placeholder = "Type your message or click the microphone to speak...";

        let errorMessage = "Speech recognition error";
        switch (event.error) {
            case 'no-speech':
                errorMessage = "No speech detected. Please try again.";
                break;
            case 'audio-capture':
                errorMessage = "Microphone not available. Please check permissions.";
                break;
            case 'not-allowed':
                errorMessage = "Microphone access denied. Please allow microphone permissions.";
                break;
            case 'network':
                errorMessage = "Network error. Please check your connection.";
                break;
            case 'service-not-allowed':
                errorMessage = "Speech service not allowed. Please try again.";
                break;
            default:
                errorMessage = `Speech error: ${event.error}`;
        }

        showSpeechStatus("❌ " + errorMessage, "error");
        showToast("❌ " + errorMessage, "error");
        
        setTimeout(() => {
            hideSpeechStatus();
        }, 4000);
    };

    recognition.onend = function() {
        console.log("🎤 Speech recognition ended");
        isListening = false;
        updateMicButton();
        chatInput.classList.remove("listening");
        chatInput.placeholder = "Type your message or click the microphone to speak...";
        
        if (speechStatus.textContent.includes("Listening")) {
            showSpeechStatus("🎤 Stopped listening", "processing");
            setTimeout(() => {
                hideSpeechStatus();
            }, 2000);
        }
    };

    console.log("✅ Speech Recognition initialized");
}

// Speech Recognition Controls
function startSpeechRecognition() {
    if (!recognition) {
        showToast("❌ Speech Recognition not available", "error");
        return;
    }

    if (isListening) {
        stopSpeechRecognition();
        return;
    }

    try {
        recognition.start();
        console.log("🎤 Starting speech recognition...");
    } catch (error) {
        console.error("❌ Failed to start speech recognition:", error);
        showToast("❌ Failed to start microphone", "error");
    }
}

function stopSpeechRecognition() {
    if (recognition && isListening) {
        recognition.stop();
        console.log("🛑 Stopping speech recognition...");
    }
}

function updateMicButton() {
    if (isListening) {
        micBtn.classList.add("listening");
        micBtn.innerHTML = "🛑";
        micBtn.title = "Stop listening";
    } else {
        micBtn.classList.remove("listening");
        micBtn.innerHTML = "🎤";
        micBtn.title = "Speech to Text";
    }
}

function showSpeechStatus(message, type) {
    speechStatus.textContent = message;
    speechStatus.className = `speech-status ${type}`;
    speechStatus.style.display = "block";
}

function hideSpeechStatus() {
    speechStatus.style.display = "none";
}

// Check Flask backend connection status
async function checkFlaskConnection() {
    try {
        console.log("🔗 Checking Flask backend connection...");
        const response = await fetch(`${BACKEND_URL}/health`);
        if (response.ok) {
            const data = await response.json();
            console.log("✅ Flask backend connection successful:", data);
            showToast("✅ Flask backend connected!", "success");
        }
    } catch (error) {
        console.warn("⚠️ Flask backend connection failed:", error);
        showToast("⚠️ Please start Flask server", "warning");
    }
}

// Setup event listeners
function setupEventListeners() {
    chatInput.addEventListener("input", function () {
        autoResizeTextarea(this);
        toggleSubmitButton();
    });

    chatInput.addEventListener("keydown", function (e) {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendMessageToFlask();
        }
    });

    submitBtn.addEventListener("click", sendMessageToFlask);
    micBtn.addEventListener("click", startSpeechRecognition);
    
    chatMessages.addEventListener("click", function () {
        if (!isTyping && !isListening) chatInput.focus();
    });

    document.addEventListener("keydown", function (e) {
        if ((e.ctrlKey || e.metaKey) && e.key === "k") {
            e.preventDefault();
            chatInput.focus();
        }
        if ((e.ctrlKey || e.metaKey) && e.key === "l") {
            e.preventDefault();
            clearChat();
        }
        if ((e.ctrlKey || e.metaKey) && e.key === "m") {
            e.preventDefault();
            startSpeechRecognition();
        }
    });

    // Handle visibility change to stop recording
    document.addEventListener("visibilitychange", function() {
        if (document.hidden && isListening) {
            stopSpeechRecognition();
        }
    });
}

// Send message to Flask backend
async function sendMessageToFlask() {
    const message = chatInput.value.trim();
    if (!message || isTyping) return;

    // Stop listening if active
    if (isListening) {
        stopSpeechRecognition();
    }

    console.log("📤 Sending message to Flask:", message);

    addMessage(message, "user");
    chatInput.value = "";
    chatInput.style.height = "auto";
    toggleSubmitButton();
    showTypingIndicator();

    try {
        // Use correct endpoint with /api prefix
        const response = await fetch(`${BACKEND_URL}/api/chat/chat`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                message: message,
                context: [],
                timestamp: new Date().toISOString(),
                user_id: "user123",
            }),
        });

        console.log("📥 Flask response status:", response.status);

        if (!response.ok) {
            let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
            try {
                const errorData = await response.json();
                errorMessage = errorData.error || errorMessage;
            } catch (e) {
                // Ignore JSON parse errors
            }
            throw new Error(errorMessage);
        }

        const result = await response.json();
        console.log("📥 Flask response data:", result);

        hideTypingIndicator();

        if (result.success) {
            const aiMessage =
                result.data?.content || result.data?.assistant_message || result.message || "Response received.";
            addMessage(aiMessage, "assistant");

            if (result.data?.sources && result.data.sources.length > 0) {
                addMessage(
                    `📖 Sources: ${result.data.sources.join(", ")}`,
                    "sources"
                );
            }

            if (result.data?.azure_services_used) {
                const services = result.data.azure_services_used;
                const serviceInfo = `🔧 Services: OpenAI(${services.openai || services.openai_embedding}), CosmosDB(${services.cosmos_db}), Docs(${services.document_results || services.document_chunks})`;
                addMessage(serviceInfo, "info");
            }
        } else {
            throw new Error(result.error || "Unknown error occurred");
        }
    } catch (error) {
        console.error("❌ Flask communication error:", error);
        hideTypingIndicator();
        addMessage(`❌ Error occurred: ${error.message}`, "assistant");
        showToast("❌ Flask backend error", "error");
    }
}

// Add document upload UI
function addDocumentUploadUI() {
    const inputContainer = chatInput.parentElement;

    const uploadBtn = document.createElement("button");
    uploadBtn.innerHTML = "📎";
    uploadBtn.title = "Upload Document";
    uploadBtn.className = "upload-btn";

    const fileInput = document.createElement("input");
    fileInput.type = "file";
    fileInput.accept = ".txt,.pdf,.docx,.md,.csv,.json";
    fileInput.style.display = "none";
    fileInput.multiple = true;

    uploadBtn.addEventListener("click", () => fileInput.click());
    fileInput.addEventListener("change", handleFileUpload);

    inputContainer.insertBefore(uploadBtn, inputContainer.querySelector('.input-controls'));
    document.body.appendChild(fileInput);
}

// Handle file upload
async function handleFileUpload(e) {
    const files = e.target.files;
    for (let file of files) {
        await uploadFileToFlask(file);
    }
}

// Upload file to Flask
async function uploadFileToFlask(file) {
    try {
        showToast(`📤 Uploading ${file.name}…`, "info");

        const formData = new FormData();
        formData.append("file", file);

        // Use correct endpoint with /api prefix
        const response = await fetch(`${BACKEND_URL}/api/documents/upload`, {
            method: "POST",
            body: formData,
        });

        const result = await response.json();

        if (response.ok && result.success) {
            showToast(`✅ "${file.name}" uploaded successfully!`, "success");
            addMessage(`📄 Uploaded: ${file.name}`, "system");
            uploadedDocuments.push({
                name: file.name,
                id: result.data?.document_id || Date.now(),
                uploadedAt: new Date().toISOString(),
            });
        } else {
            throw new Error(result.error || result.message || "Upload failed");
        }
    } catch (error) {
        console.error("Upload error:", error);
        showToast(`❌ "${file.name}" upload failed`, "error");
    }
}

// Add a message to chat
function addMessage(content, sender) {
    const messageDiv = document.createElement("div");
    messageDiv.className = `message ${sender}`;

    const avatar = document.createElement("div");
    avatar.className = "message-avatar";

    switch (sender) {
        case "user":
            avatar.textContent = "👤";
            messageDiv.style.justifyContent = "flex-end";
            break;
        case "assistant":
            avatar.textContent = "🤖";
            break;
        case "system":
            avatar.textContent = "⚙️";
            messageDiv.style.opacity = "0.8";
            break;
        case "sources":
            avatar.textContent = "📖";
            messageDiv.style.fontSize = "0.9em";
            messageDiv.style.opacity = "0.7";
            break;
        case "info":
            avatar.textContent = "ℹ️";
            messageDiv.style.fontSize = "0.85em";
            messageDiv.style.opacity = "0.6";
            break;
        default:
            avatar.textContent = "🤖";
    }

    const bubble = document.createElement("div");
    bubble.className = "message-bubble";
    bubble.innerHTML = formatMessage(content);

    messageDiv.appendChild(avatar);
    messageDiv.appendChild(bubble);

    const welcomeMessage = document.querySelector(".welcome-message");
    if (welcomeMessage) welcomeMessage.remove();

    chatMessages.appendChild(messageDiv);
    scrollToBottom();
}

// Format message content (auto-link URLs)
function formatMessage(content) {
    return content.replace(
        /(https?:\/\/[^\s]+)/g,
        '<a href="$1" target="_blank">$1</a>'
    );
}

// Show welcome message
function showWelcomeMessage() {
    const welcomeDiv = document.createElement("div");
    welcomeDiv.className = "welcome-message";
    welcomeDiv.innerHTML = `
        <h3>🚀 AI Assistant with Speech</h3>
        <p>AI Chat with Speech-to-Text integration!</p>
        <div class="welcome-features">
            Type, speak, or upload documents • Click 🎤 to use voice input<br>
            <small>Shortcuts: Ctrl+M (Mic) | Ctrl+K (Focus) | Ctrl+L (Clear)</small>
        </div>
    `;
    chatMessages.appendChild(welcomeDiv);
}

// Utility functions
function autoResizeTextarea(textarea) {
    textarea.style.height = "auto";
    textarea.style.height = Math.min(textarea.scrollHeight, 120) + "px";
}

function toggleSubmitButton() {
    const hasText = chatInput.value.trim().length > 0;
    submitBtn.disabled = !hasText || isTyping;
    submitBtn.style.opacity = hasText && !isTyping ? "1" : "0.5";
}

function showTypingIndicator() {
    isTyping = true;
    if (typingIndicator) typingIndicator.style.display = "flex";
    toggleSubmitButton();
    scrollToBottom();
}

function hideTypingIndicator() {
    isTyping = false;
    if (typingIndicator) typingIndicator.style.display = "none";
    toggleSubmitButton();
}

function scrollToBottom() {
    chatMessages.scrollTo({
        top: chatMessages.scrollHeight,
        behavior: "smooth",
    });
}

function clearChat() {
    chatMessages.innerHTML = "";
    showWelcomeMessage();
    chatInput.focus();
    showToast("🧹 Chat cleared", "info");
}

function showToast(message, type = "info", duration = 3000) {
    const toast = document.createElement("div");
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 12px 20px;
        border-radius: 8px;
        color: white;
        font-weight: 500;
        z-index: 1000;
        min-width: 250px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        animation: slideIn 0.3s ease;
    `;

    const colors = {
        success: "#28a745",
        error: "#dc3545",
        warning: "#ffc107",
        info: "#17a2b8",
    };

    toast.style.backgroundColor = colors[type] || colors.info;
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = "slideOut 0.3s ease";
        setTimeout(() => {
            if (document.body.contains(toast)) {
                document.body.removeChild(toast);
            }
        }, 300);
    }, duration);
}

// Debug information
console.log("🔧 Flask backend URL:", BACKEND_URL);
console.log("🔧 Speech Recognition available:", !!recognition);
console.log("🔧 Shortcuts: Ctrl+M (Mic), Ctrl+K (Focus), Ctrl+L (Clear)");