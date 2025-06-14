
# 🌐 Gomm AI — Frontend UI

This folder contains the basic web frontend for the **Gomm AI** GenAI-powered personal assistant. It allows users to interact with AI through a browser based chatbot interface that supports both text and speech input.

The frontend is lightweight and customizable, built using standard HTML, CSS, and JavaScript. This `README` outlines how to set it up and modify key configurations.



---
## 🚀 How to Run
Open your Visual studio terminal
Make sure your backend server (Flask) is running before launching the frontend.

To run the frontend:
1. Open your terminal in the `frontend` directory.
2. Run:
   ```bash
   npm install
   npm start
---

## 🔧 Configuration (Optional)

If your frontend communicates with a backend (e.g., Flask or Azure Function), update the API URL in `script.js`:

```js
// Example API base URL
const API_BASE = "http://localhost:5000/api";
```

---

## 🎨 Customisation Options

* **Chat UI**: Edit `index.html` and `style.css` to change the chatbot interface appearance.
* **Speech-to-Text**: Make sure your browser supports the Web Speech API for voice input.
* **Response Handling**: Update `script.js` to modify how responses are received and displayed.

---

## 🛠 Key Files to Modify

* `index.html`: Layout and chatbot interface structure
* `script.js`: Handles user input, API communication, and displaying responses
* `styles.css`: Controls visual styles (e.g., colors, layout, animations)

---

## 📌 Notes

* This frontend is intended to work with the Gomm AI backend (Flask + Azure services).
* If you're uploading files to Azure Blob Storage, ensure CORS is enabled on the backend.
* In production, secure all API endpoints and sanitize user input.

---

## 🧪 Troubleshooting

* **CORS errors**: Ensure CORS is enabled on your backend.
* **Voice input not working**: Check browser compatibility.
* **Slow responses**: If OpenAI processing is slow, consider chunking large documents.


