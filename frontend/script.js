// Enhanced AI Chat Interface with FlashCards
console.log("🚀 AI Assistant with FlashCards Started");

// Global variables
let isTyping = false;
let isListening = false;
let recognition = null;
let uploadedDocuments = [];
const BACKEND_URL = "http://127.0.0.1:5000";

// FlashCard variables
let currentUserId = 'demo_user_' + Math.random().toString(36).substr(2, 9);
let currentSection = 'chat';
let conversationHistory = [];
let canCreateFlashcard = false;
let reviewCards = [];
let currentReviewIndex = 0;
let currentCard = null;
let cardFlipped = false;
let reviewStartTime = null;

// DOM elements
let chatInput, chatMessages, submitBtn, typingIndicator, micBtn, speechStatus, flashcardBtn;

// Initialization
document.addEventListener("DOMContentLoaded", function () {
    console.log("🤖 AI Assistant Initializing...");

    // Get DOM elements
    chatInput = document.getElementById("chatInput");
    chatMessages = document.getElementById("chatMessages");
    submitBtn = document.getElementById("submitBtn");
    typingIndicator = document.getElementById("typingIndicator");
    micBtn = document.getElementById("micBtn");
    speechStatus = document.getElementById("speechStatus");
    flashcardBtn = document.getElementById("flashcardBtn");

    if (!chatInput || !chatMessages || !submitBtn || !micBtn) {
        console.error("❌ Essential DOM elements not found");
        showToast("❌ UI components not found", "error");
        return;
    }

    chatInput.focus();
    setupEventListeners();
    setupSpeechRecognition();
    addDocumentUploadUI();
    showWelcomeMessage();
    checkFlaskConnection();
    loadStats();
    
    console.log('🧠 FlashCard system initialized with user ID:', currentUserId);
});

// Speech Recognition Setup
function setupSpeechRecognition() {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
        console.warn("⚠️ Speech Recognition not supported");
        if (micBtn) {
            micBtn.disabled = true;
            micBtn.title = "Speech Recognition not supported";
            micBtn.style.opacity = "0.3";
        }
        return;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = 'en-US';
    recognition.maxAlternatives = 1;

    recognition.onstart = function() {
        console.log("🎤 Speech recognition started");
        isListening = true;
        updateMicButton();
        showSpeechStatus("🎤 Listening... Speak now!", "listening");
        if (chatInput) {
            chatInput.classList.add("listening");
            chatInput.placeholder = "Listening... Speak your message";
        }
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

        if (interimTranscript && chatInput) {
            chatInput.value = finalTranscript + interimTranscript;
            showSpeechStatus("🎤 " + interimTranscript, "listening");
        }

        if (finalTranscript && chatInput) {
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
        
        if (chatInput) {
            chatInput.classList.remove("listening");
            chatInput.placeholder = "Type your message or click the microphone to speak...";
        }

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
        
        if (chatInput) {
            chatInput.classList.remove("listening");
            chatInput.placeholder = "Type your message or click the microphone to speak...";
        }
        
        if (speechStatus && speechStatus.textContent.includes("Listening")) {
            showSpeechStatus("🎤 Stopped listening", "processing");
            setTimeout(() => {
                hideSpeechStatus();
            }, 2000);
        }
    };

    console.log("✅ Speech Recognition initialized");
}

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
    if (!micBtn) return;
    
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
    if (!speechStatus) return;
    
    speechStatus.textContent = message;
    speechStatus.className = `speech-status ${type}`;
    speechStatus.style.display = "block";
}

function hideSpeechStatus() {
    if (speechStatus) {
        speechStatus.style.display = "none";
    }
}

// Connection check
async function checkFlaskConnection() {
    try {
        console.log("🔗 Checking Flask backend connection...");
        const response = await fetch(`${BACKEND_URL}/health`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            },
        });
        
        if (response.ok) {
            const data = await response.json();
            console.log("✅ Flask backend connection successful:", data);
            showToast("✅ Flask backend connected!", "success");
        } else {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
    } catch (error) {
        console.warn("⚠️ Flask backend connection failed:", error);
        showToast("⚠️ Please start Flask server", "warning");
    }
}

// Event listeners
function setupEventListeners() {
    if (chatInput) {
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
    }

    if (submitBtn) {
        submitBtn.addEventListener("click", sendMessageToFlask);
    }
    
    if (micBtn) {
        micBtn.addEventListener("click", startSpeechRecognition);
    }

    if (flashcardBtn) {
        flashcardBtn.addEventListener("click", createFlashcardFromChat);
    }
    
    if (chatMessages) {
        chatMessages.addEventListener("click", function () {
            if (!isTyping && !isListening && chatInput) {
                chatInput.focus();
            }
        });
    }

    // Navigation listeners
    document.querySelectorAll('.nav-button').forEach(button => {
        button.addEventListener('click', (e) => {
            const section = e.target.dataset.section;
            switchSection(section);
        });
    });

    // Keyboard shortcuts
    document.addEventListener("keydown", function (e) {
        if ((e.ctrlKey || e.metaKey) && e.key === "k") {
            e.preventDefault();
            if (chatInput) chatInput.focus();
        }
        if ((e.ctrlKey || e.metaKey) && e.key === "l") {
            e.preventDefault();
            clearChat();
        }
        if ((e.ctrlKey || e.metaKey) && e.key === "m") {
            e.preventDefault();
            startSpeechRecognition();
        }
        if ((e.ctrlKey || e.metaKey) && e.key === "d") {
            e.preventDefault();
            debugAzureSearch();
        }
        if ((e.ctrlKey || e.metaKey) && e.key === "f") {
            e.preventDefault();
            if (canCreateFlashcard) createFlashcardFromChat();
        }
    });

    // Handle visibility change
    document.addEventListener("visibilitychange", function() {
        if (document.hidden && isListening) {
            stopSpeechRecognition();
        }
    });

    // Debug buttons
    const debugBtn = document.getElementById('debugBtn');
    const clearBtn = document.getElementById('clearBtn');
    
    if (debugBtn) {
        debugBtn.addEventListener("click", debugAzureSearch);
    }
    
    if (clearBtn) {
        clearBtn.addEventListener("click", clearChat);
    }
}

// FlashCard functions
function isFlashcardRequest(message) {
    const keywords = ['create flashcard', 'make flashcard', 'save as flashcard', 'flashcard this', 'make a card'];
    return keywords.some(keyword => message.toLowerCase().includes(keyword));
}

function storeConversation(userMessage, aiResponse) {
    conversationHistory.push({
        user_message: userMessage,
        ai_response: aiResponse,
        timestamp: new Date().toISOString()
    });
    
    if (conversationHistory.length > 5) {
        conversationHistory = conversationHistory.slice(-5);
    }
    
    canCreateFlashcard = true;
    if (flashcardBtn) {
        flashcardBtn.disabled = false;
        flashcardBtn.classList.add("enabled");
        flashcardBtn.title = "Create FlashCard from last conversation";
    }
}

async function createFlashcardFromChat() {
    if (!canCreateFlashcard || conversationHistory.length === 0) {
        addMessage("❌ No recent conversation found to create flashcard from.", "assistant");
        return;
    }

    const lastConversation = conversationHistory[conversationHistory.length - 1];
    
    showTypingIndicator();

    try {
        const response = await fetch(`${BACKEND_URL}/api/flashcards/from-chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                user_id: currentUserId,
                user_message: lastConversation.user_message,
                ai_response: lastConversation.ai_response,
                context: conversationHistory.slice(-3)
            })
        });

        const result = await response.json();
        hideTypingIndicator();
        
        if (result.success) {
            handleFlashcardCreationResponse(result);
        } else {
            addMessage(`❌ Failed to create flashcard: ${result.error}`, "assistant");
        }
    } catch (error) {
        hideTypingIndicator();
        addMessage(`❌ Failed to create flashcard: ${error.message}`, "assistant");
    }
}

// FIXED: Updated function to show simple toast instead of large popup
function handleFlashcardCreationResponse(result) {
    const flashcardData = result.data?.flashcard || result.flashcard_result?.flashcard || result.flashcard;
    
    if (flashcardData) {
        // FIXED: Simple toast notification instead of large chat message
        const cardPreview = flashcardData.front.length > 50 
            ? flashcardData.front.substring(0, 47) + "..." 
            : flashcardData.front;
        
        showToast(`✅ FlashCard created: "${cardPreview}"`, "success", 4000);
        
        // Optional: Update sidebar stats immediately
        if (document.getElementById('totalCards')) {
            const currentTotal = parseInt(document.getElementById('totalCards').textContent) || 0;
            document.getElementById('totalCards').textContent = currentTotal + 1;
        }
    }

    canCreateFlashcard = false;
    if (flashcardBtn) {
        flashcardBtn.disabled = true;
        flashcardBtn.classList.remove("enabled");
        flashcardBtn.title = "Create FlashCard from conversation";
        
        // Visual feedback on button
        const originalHTML = flashcardBtn.innerHTML;
        flashcardBtn.innerHTML = "✅";
        flashcardBtn.style.background = "#28a745";
        
        setTimeout(() => {
            flashcardBtn.innerHTML = originalHTML;
            flashcardBtn.style.background = "";
        }, 2000);
    }

    loadStats();
}

// Main chat function
async function sendMessageToFlask() {
    if (!chatInput) return;
    
    const message = chatInput.value.trim();
    if (!message || isTyping) return;

    if (isListening) {
        stopSpeechRecognition();
    }

    console.log("📤 Sending message to Flask:", message);

    addMessage(message, "user");
    chatInput.value = "";
    chatInput.style.height = "auto";
    toggleSubmitButton();
    showTypingIndicator();

    if (isFlashcardRequest(message)) {
        hideTypingIndicator();
        await createFlashcardFromChat();
        return;
    }

    try {
        const response = await fetch(`${BACKEND_URL}/api/chat/chat`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                message: message,
                context: [],
                timestamp: new Date().toISOString(),
                user_id: currentUserId,
            }),
        });

        console.log("📥 Flask response status:", response.status);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const responseText = await response.text();
        console.log("📥 Flask raw response length:", responseText.length);

        let result;
        try {
            result = JSON.parse(responseText);
        } catch (parseError) {
            console.error("❌ Failed to parse JSON response:", parseError);
            throw new Error(`Invalid JSON response from server`);
        }

        console.log("📥 Flask parsed response:", result);
        hideTypingIndicator();

        let aiMessage = null;
        let sources = [];
        let serviceInfo = null;

        if (result.success) {
            aiMessage = result.data?.assistant_message ||
                       result.data?.content ||
                       result.assistant_message ||
                       result.content ||
                       result.message ||
                       "Response received but content not found.";
            
            sources = result.data?.sources || result.sources || [];
            
            const services = result.data?.azure_services_used || result.azure_services_used;
            if (services) {
                const serviceNames = [];
                if (services.openai || services.openai_embedding) serviceNames.push('OpenAI');
                if (services.cosmos_db) serviceNames.push('CosmosDB');
                if (services.azure_ai_search) serviceNames.push('Azure AI Search');
                if (services.notion_search) serviceNames.push('Notion');
                if (services.flashcard_service) serviceNames.push('FlashCards');
                
                const docCount = services.document_chunks || services.document_results || 0;
                serviceInfo = `🔧 Services: ${serviceNames.join(', ')} | Documents: ${docCount}`;
            }

            if (result.data?.type === 'flashcard_creation' || result.data?.flashcard_result) {
                handleFlashcardCreationResponse(result.data);
                return;
            }

            if (result.data?.notion_integration || result.notion_integration) {
                const notion = result.data?.notion_integration || result.notion_integration;
                if (notion.success) {
                    aiMessage += `\n\n✅ **Saved to Notion page: '${notion.target_page}'**`;
                } else if (notion.requested) {
                    aiMessage += `\n\n❌ **Failed to save to Notion:** ${notion.error}`;
                }
            }

        } else {
            aiMessage = result.error || result.message || "An error occurred while processing your request.";
        }

        if (!aiMessage || aiMessage.trim() === "") {
            console.warn("⚠️ No message content found in response");
            aiMessage = "I received your message but couldn't extract the response content. Please try again.";
        }

        addMessage(aiMessage, "assistant");
        storeConversation(message, aiMessage);

        if (sources && sources.length > 0) {
            addMessage(`📖 Sources: ${sources.join(", ")}`, "sources");
        }

        if (serviceInfo) {
            addMessage(serviceInfo, "info");
        }

        console.log("✅ Response processed successfully");

    } catch (error) {
        console.error("❌ Flask communication error:", error);
        hideTypingIndicator();
        
        let errorMessage = "Unable to connect to the AI service.";
        
        if (error.message.includes('fetch')) {
            errorMessage = "Connection failed. Please check if the Flask server is running on port 5000.";
        } else if (error.message.includes('JSON')) {
            errorMessage = "Server returned invalid response. Check server logs.";
        } else if (error.message.includes('HTTP')) {
            errorMessage = `Server error: ${error.message}`;
        } else {
            errorMessage = error.message;
        }
        
        addMessage(`❌ Error: ${errorMessage}`, "assistant");
        showToast("❌ Communication error - check console for details", "error");
    }
}

// Section switching
function switchSection(section) {
    document.querySelectorAll('.nav-button').forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelector(`[data-section="${section}"]`).classList.add('active');

    document.querySelectorAll('.section').forEach(sec => {
        sec.style.display = 'none';
    });

    document.getElementById(`${section}Section`).style.display = 'block';
    currentSection = section;

    const headers = {
        chat: { title: 'AI Chat Assistant', desc: 'Ask me anything and create flashcards from our conversation!' },
        review: { title: 'FlashCard Review', desc: 'Practice with spaced repetition for optimal learning' },
        flashcards: { title: 'My FlashCards', desc: 'Manage and organize your study cards' },
        stats: { title: 'Learning Statistics', desc: 'Track your progress and performance' }
    };

    document.getElementById('sectionTitle').textContent = headers[section].title;
    document.getElementById('sectionDescription').textContent = headers[section].desc;

    if (section === 'review') {
        loadReviewCards();
    } else if (section === 'flashcards') {
        loadFlashcards();
    } else if (section === 'stats') {
        loadDetailedStats();
    }
}

// Stats loading
async function loadStats() {
    try {
        const response = await fetch(`${BACKEND_URL}/api/flashcards/stats?user_id=${currentUserId}`);
        const result = await response.json();
        
        if (result.success) {
            const stats = result.data;
            document.getElementById('totalCards').textContent = stats.total_flashcards || 0;
            document.getElementById('dueToday').textContent = stats.due_for_review || 0;
            document.getElementById('accuracy').textContent = (stats.accuracy || 0) + '%';
            document.getElementById('streak').textContent = stats.longest_streak || 0;
        }
    } catch (error) {
        console.error('Failed to load stats:', error);
    }
}

// Review functions
async function loadReviewCards() {
    try {
        const response = await fetch(`${BACKEND_URL}/api/flashcards/review/due?user_id=${currentUserId}&limit=20`);
        const result = await response.json();
        
        if (result.success) {
            reviewCards = result.data.flashcards || [];
            currentReviewIndex = 0;
            
            if (reviewCards.length > 0) {
                startReviewSession();
            } else {
                showEmptyReviewState();
            }
        }
    } catch (error) {
        console.error('Failed to load review cards:', error);
        showEmptyReviewState();
    }
}

function startReviewSession() {
    const reviewContent = document.getElementById('reviewContent');
    const progressElement = document.getElementById('reviewProgress');
    
    document.getElementById('totalReviewCards').textContent = reviewCards.length;
    progressElement.style.display = 'block';
    
    showReviewCard();
}

function showReviewCard() {
    if (currentReviewIndex >= reviewCards.length) {
        completeReviewSession();
        return;
    }

    currentCard = reviewCards[currentReviewIndex];
    cardFlipped = false;
    reviewStartTime = Date.now();

    const reviewContent = document.getElementById('reviewContent');
    document.getElementById('currentCard').textContent = currentReviewIndex + 1;
    
    const progressPercent = ((currentReviewIndex) / reviewCards.length) * 100;
    document.getElementById('progressFill').style.width = progressPercent + '%';

    reviewContent.innerHTML = `
        <div class="flashcard" onclick="flipCard()">
            <div class="flashcard-meta">
                Difficulty: ${currentCard.difficulty || 3}/5 | Tags: ${currentCard.tags?.join(', ') || 'None'}
            </div>
            <div class="flashcard-content">
                <div class="flashcard-front">${currentCard.front}</div>
            </div>
        </div>
        <p style="margin-top: 20px; color: #666;">Click the card to reveal the answer</p>
    `;
}

function flipCard() {
    if (cardFlipped) return;
    
    cardFlipped = true;
    const flashcard = document.querySelector('.flashcard');
    const content = document.querySelector('.flashcard-content');
    
    flashcard.classList.add('flipped');
    content.innerHTML = `
        <div class="flashcard-back">${currentCard.back}</div>
        ${currentCard.mnemonic ? `<div style="margin-top: 15px; font-size: 14px; opacity: 0.8;">💡 ${currentCard.mnemonic}</div>` : ''}
    `;

    const reviewContent = document.getElementById('reviewContent');
    reviewContent.innerHTML += `
        <div class="review-controls">
            <button class="review-button incorrect" onclick="submitReview(false)">
                ❌ Incorrect
            </button>
            <button class="review-button correct" onclick="submitReview(true)">
                ✅ Correct
            </button>
        </div>
    `;
}

async function submitReview(correct) {
    const responseTime = Date.now() - reviewStartTime;

    try {
        const response = await fetch(`${BACKEND_URL}/api/flashcards/review/submit`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                user_id: currentUserId,
                flashcard_id: currentCard.id,
                correct: correct,
                response_time: responseTime
            })
        });

        const result = await response.json();
        
        currentReviewIndex++;
        setTimeout(() => {
            showReviewCard();
        }, 1000);
    } catch (error) {
        console.error('Failed to submit review:', error);
        currentReviewIndex++;
        setTimeout(() => {
            showReviewCard();
        }, 1000);
    }
}

function completeReviewSession() {
    const reviewContent = document.getElementById('reviewContent');
    document.getElementById('progressFill').style.width = '100%';
    
    reviewContent.innerHTML = `
        <div class="empty-state">
            <h3>🎉 Review Session Complete!</h3>
            <p>Great job! You've reviewed all your cards for today.</p>
            <button class="cta-button" onclick="switchSection('chat')">Continue Learning</button>
        </div>
    `;

    loadStats();
}

function showEmptyReviewState() {
    const reviewContent = document.getElementById('reviewContent');
    document.getElementById('reviewProgress').style.display = 'none';
    
    reviewContent.innerHTML = `
        <div class="empty-state">
            <h3>🎉 No cards due for review!</h3>
            <p>Come back later or create more flashcards from your conversations.</p>
            <button class="cta-button" onclick="switchSection('chat')">Start Chatting</button>
        </div>
    `;
}

// FlashCard list management
async function loadFlashcards() {
    const flashcardsList = document.getElementById('flashcardsList');
    
    try {
        const response = await fetch(`${BACKEND_URL}/api/flashcards/list?user_id=${currentUserId}&limit=50`);
        const result = await response.json();
        
        if (result.success) {
            const flashcards = result.data.flashcards || [];
            
            if (flashcards.length === 0) {
                flashcardsList.innerHTML = `
                    <div class="empty-state" style="grid-column: 1 / -1;">
                        <h3>📚 No flashcards yet</h3>
                        <p>Start by having a conversation and creating your first flashcard!</p>
                        <button class="cta-button" onclick="switchSection('chat')">Start Chatting</button>
                    </div>
                `;
                return;
            }

            flashcardsList.innerHTML = flashcards.map(card => `
                <div class="flashcard-item">
                    <div class="flashcard-item-header">
                        <span class="flashcard-difficulty ${getDifficultyClass(card.difficulty)}">
                            ${getDifficultyText(card.difficulty)}
                        </span>
                        <small>${new Date(card.created_date).toLocaleDateString()}</small>
                    </div>
                    <div style="margin-bottom: 10px;">
                        <strong>Q:</strong> ${card.front}
                    </div>
                    <div style="margin-bottom: 10px;">
                        <strong>A:</strong> ${card.back}
                    </div>
                    <div class="flashcard-tags">
                        ${(card.tags || []).map(tag => `<span class="tag">${tag}</span>`).join('')}
                    </div>
                    ${card.mnemonic ? `<div style="margin: 10px 0; font-size: 12px; color: #666;">💡 ${card.mnemonic}</div>` : ''}
                    <div class="flashcard-actions">
                        <button class="action-button edit" onclick="editFlashcard('${card.id}')">Edit</button>
                        <button class="action-button delete" onclick="deleteFlashcard('${card.id}')">Delete</button>
                    </div>
                </div>
            `).join('');
        } else {
            flashcardsList.innerHTML = `<div class="loading">Failed to load flashcards</div>`;
        }
    } catch (error) {
        console.error('Failed to load flashcards:', error);
        flashcardsList.innerHTML = `<div class="loading">Failed to load flashcards</div>`;
    }
}

function getDifficultyClass(difficulty) {
    if (difficulty <= 2) return 'easy';
    if (difficulty <= 3) return 'medium';
    return 'hard';
}

function getDifficultyText(difficulty) {
    if (difficulty <= 2) return 'Easy';
    if (difficulty <= 3) return 'Medium';
    return 'Hard';
}

async function deleteFlashcard(flashcardId) {
    if (!confirm('Are you sure you want to delete this flashcard?')) return;

    try {
        const response = await fetch(`${BACKEND_URL}/api/flashcards/delete/${flashcardId}?user_id=${currentUserId}`, {
            method: 'DELETE'
        });

        const result = await response.json();
        
        if (result.success) {
            loadFlashcards();
            loadStats();
        } else {
            alert('Failed to delete flashcard: ' + result.error);
        }
    } catch (error) {
        alert('Failed to delete flashcard: ' + error.message);
    }
}

function editFlashcard(flashcardId) {
    alert('Edit functionality coming soon!');
}

// Detailed stats
async function loadDetailedStats() {
    const statsContainer = document.querySelector('.stats-container');
    
    try {
        const response = await fetch(`${BACKEND_URL}/api/flashcards/stats?user_id=${currentUserId}`);
        const result = await response.json();
        
        if (result.success) {
            const stats = result.data;
            
            statsContainer.innerHTML = `
                <div class="stats-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px;">
                    <div class="stat-card" style="background: white; padding: 20px; border-radius: 10px; box-shadow: 0 5px 15px rgba(0,0,0,0.1);">
                        <h3 style="color: #4facfe; margin-bottom: 15px;">📚 Learning Overview</h3>
                        <div style="margin: 10px 0;"><strong>Total FlashCards:</strong> ${stats.total_flashcards || 0}</div>
                        <div style="margin: 10px 0;"><strong>Total Reviews:</strong> ${stats.total_reviews || 0}</div>
                        <div style="margin: 10px 0;"><strong>Cards Due Today:</strong> ${stats.due_for_review || 0}</div>
                    </div>
                    
                    <div class="stat-card" style="background: white; padding: 20px; border-radius: 10px; box-shadow: 0 5px 15px rgba(0,0,0,0.1);">
                        <h3 style="color: #28a745; margin-bottom: 15px;">🎯 Performance</h3>
                        <div style="margin: 10px 0;"><strong>Accuracy:</strong> ${stats.accuracy || 0}%</div>
                        <div style="margin: 10px 0;"><strong>Correct Answers:</strong> ${stats.total_correct || 0}</div>
                        <div style="margin: 10px 0;"><strong>Longest Streak:</strong> ${stats.longest_streak || 0}</div>
                    </div>
                    
                    <div class="stat-card" style="background: white; padding: 20px; border-radius: 10px; box-shadow: 0 5px 15px rgba(0,0,0,0.1);">
                        <h3 style="color: #6f42c1; margin-bottom: 15px;">⚡ Advanced Stats</h3>
                        <div style="margin: 10px 0;"><strong>Avg. Ease Factor:</strong> ${stats.average_ease_factor || 2.5}</div>
                        <div style="margin: 10px 0;"><strong>Last Updated:</strong> ${new Date(stats.last_updated || Date.now()).toLocaleDateString()}</div>
                    </div>
                </div>
                
                <div style="margin-top: 30px; text-align: center;">
                    <button class="cta-button" onclick="switchSection('review')">Start Review Session</button>
                </div>
            `;
        } else {
            statsContainer.innerHTML = `<div class="loading">Failed to load statistics</div>`;
        }
    } catch (error) {
        console.error('Failed to load detailed stats:', error);
        statsContainer.innerHTML = `<div class="loading">Failed to load statistics</div>`;
    }
}

// Document upload
function addDocumentUploadUI() {
    if (!chatInput) return;
    
    const inputContainer = chatInput.parentElement;
    if (!inputContainer) return;

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

    const inputControls = inputContainer.querySelector('.input-controls');
    if (inputControls) {
        inputContainer.insertBefore(uploadBtn, inputControls);
    } else {
        inputContainer.appendChild(uploadBtn);
    }
    
    document.body.appendChild(fileInput);
}

async function handleFileUpload(e) {
    const files = e.target.files;
    for (let file of files) {
        await uploadFileToFlask(file);
    }
}

async function uploadFileToFlask(file) {
    try {
        showToast(`📤 Uploading ${file.name}…`, "info");

        const formData = new FormData();
        formData.append("file", file);

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

// Debug function
async function debugAzureSearch() {
    try {
        showToast("🔍 Checking Azure AI Search contents...", "info");
        
        const response = await fetch(`${BACKEND_URL}/api/chat/debug/azure-search`, {
            method: "GET",
            headers: {
                "Content-Type": "application/json",
            },
        });

        const result = await response.json();
        
        if (response.ok && result.success) {
            console.log("🔍 Azure AI Search Debug Results:", result.data);
            
            const diagnosis = result.data.diagnosis || {};
            const indexInfo = result.data.index_info || {};
            const documentAnalysis = result.data.document_analysis || {};
            
            let debugMessage = `🔍 **Azure AI Search Debug Results**\n\n`;
            debugMessage += `📊 **Index Status**: ${diagnosis.index_status || 'unknown'}\n`;
            debugMessage += `📄 **Total Documents**: ${indexInfo.total_documents_found || 0}\n`;
            debugMessage += `📁 **Unique Files**: ${documentAnalysis.file_count || 0}\n`;
            debugMessage += `✅ **Has Real Data**: ${documentAnalysis.has_real_documents ? 'Yes' : 'No'}\n`;
            debugMessage += `🧪 **Has Test Data**: ${documentAnalysis.has_test_documents ? 'Yes' : 'No'}\n\n`;
            
            if (diagnosis.problems_found && diagnosis.problems_found.length > 0) {
                debugMessage += `❌ **Problems Found**:\n`;
                diagnosis.problems_found.forEach(problem => {
                    debugMessage += `• ${problem}\n`;
                });
                debugMessage += `\n`;
            }
            
            if (diagnosis.recommended_solutions && diagnosis.recommended_solutions.length > 0) {
                debugMessage += `💡 **Recommended Solutions**:\n`;
                diagnosis.recommended_solutions.forEach(solution => {
                    debugMessage += `• ${solution}\n`;
                });
            }
            
            addMessage(debugMessage, "system");
            showToast("✅ Azure AI Search debug completed", "success");
        } else {
            throw new Error(result.error || "Debug request failed");
        }
    } catch (error) {
        console.error("❌ Azure Search debug error:", error);
        addMessage(`❌ **Azure AI Search Debug Failed**: ${error.message}`, "system");
        showToast("❌ Debug failed", "error");
    }
}

// Message functions
function addMessage(content, sender) {
    if (!chatMessages) return;
    
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
        case "flashcard":
            avatar.textContent = "🧠";
            messageDiv.classList.add("flashcard-success");
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

function formatMessage(content) {
    if (typeof content !== 'string') {
        content = String(content);
    }
    
    content = content.replace(
        /(https?:\/\/[^\s]+)/g,
        '<a href="$1" target="_blank">$1</a>'
    );
    
    content = content.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    content = content.replace(/\*(.*?)\*/g, '<em>$1</em>');
    content = content.replace(/\n/g, '<br>');
    
    return content;
}

function showWelcomeMessage() {
    if (!chatMessages) return;
    
    const welcomeDiv = document.createElement("div");
    welcomeDiv.className = "welcome-message";
    welcomeDiv.innerHTML = `
        <h3>🚀 AI Assistant with Speech & FlashCards</h3>
        <p>Enhanced AI Chat with Speech-to-Text, Document Search & Smart FlashCards!</p>
        <div class="welcome-features">
            Type, speak, or upload documents • Click 🎤 to use voice • Click 📚 to create flashcards<br>
            <small>Shortcuts: Ctrl+M (Mic) | Ctrl+K (Focus) | Ctrl+L (Clear) | Ctrl+D (Debug) | Ctrl+F (FlashCard)</small>
        </div>
    `;
    chatMessages.appendChild(welcomeDiv);
}

// Utility functions
function autoResizeTextarea(textarea) {
    if (!textarea) return;
    
    textarea.style.height = "auto";
    textarea.style.height = Math.min(textarea.scrollHeight, 120) + "px";
}

function toggleSubmitButton() {
    if (!submitBtn || !chatInput) return;
    
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
    if (!chatMessages) return;
    
    setTimeout(() => {
        chatMessages.scrollTo({
            top: chatMessages.scrollHeight,
            behavior: "smooth",
        });
    }, 100);
}

function clearChat() {
    if (!chatMessages) return;
    
    chatMessages.innerHTML = "";
    showWelcomeMessage();
    if (chatInput) chatInput.focus();
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
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    `;

    const colors = {
        success: "#28a745",
        error: "#dc3545", 
        warning: "#ffc107",
        info: "#17a2b8",
    };

    toast.style.backgroundColor = colors[type] || colors.info;
    if (type === 'warning') {
        toast.style.color = '#000';
    }
    
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

// Make functions available globally
window.flipCard = flipCard;
window.submitReview = submitReview;
window.switchSection = switchSection;
window.editFlashcard = editFlashcard;
window.deleteFlashcard = deleteFlashcard;

console.log("🔧 Enhanced Flask backend URL:", BACKEND_URL);
console.log("🔧 Speech Recognition available:", !!recognition);
console.log("🔧 FlashCard system initialized with user ID:", currentUserId);
console.log("🔧 Complete system with FlashCard functionality ready");