# 🧠 Gomm AI — GenAI-Based Personal Assistant

![App Preview](https://github.com/NAry-Byun/CWB_Hackathon-2025/blob/main/frontend/src/imag/Screenshot%202025-06-06%20193929.png?raw=true)

---

## 🔧 Problem Statement

In today’s digital world, we’re overwhelmed by information—documents, blogs, meeting notes, and articles pile up without structure. Finding insights, making decisions, or recalling details becomes increasingly difficult, especially without a standardized process.

---

## 💡 What is Gomm AI?

**Gomm AI** is a GenAI-powered personal assistant designed to help users manage, organize, and interact with large volumes of content—whether personal or team-based. Whether you're a student, researcher, or professional, Gomm AI simplifies learning, enhances productivity, and supports smarter decision-making.



---

## 📘 Example Use Case

> **Rahul**, a product manager, uploads meeting notes, blog links, and internal documentation.  
> An urgent meeting is scheduled in an hour. The person originally in charge is on sick leave, and Rahul must take over the presentation.  
> He needs to quickly prepare and understand the key concepts from his own documents.  
>
> He asks:  
> “What were the key decisions from last month’s planning meetings?”  
> “Summarize the 2024 business plan.”  
> “Add the summary to the Notion page.”  
>  
> Gomm AI provides a smart, context-aware summary, saving time and boosting clarity.

---
## 🏗️ Solution Architecture

<img src="https://github.com/NAry-Byun/CWB_Hackathon-2025/blob/main/frontend/src/imag/AI%20Personal%20Assistant%20App.gif?raw=true" alt="Architecture Diagram" width="900"/>

This workflow illustrates how an AI personal assistant processes raw data and enables users to interact with it through a chatbot.
Users begin by uploading various types of content such as meeting documents, business plans (PDFs), or text gathered from web scraping. These files are stored in **Azure Blob Storage**.
Once a file is uploaded, an **Azure Function Trigger** is automatically activated. This serverless function processes the file, extracts its contents, and saves the structured data into **Azure Cosmos DB**.
The stored data is then utilized by the AI assistant. 

At the same time, **Azure AI Search** indexes the content, allowing relevant information to be retrieved quickly when the user asks a question.
Using **OpenAI models**, the assistant analyzes the stored content, understands user queries, and generates meaningful, context aware responses. The system also stores chat history in Cosmos DB to maintain continuity in conversations.
If **Notion** is integrated, the assistant can fetch content directly from Notion pages or update them with AI-generated summaries and insights using the Python `notion-client` library.
Users interact with the chatbot through text or voice input. The chatbot forwards the message to OpenAI, fetches relevant information from indexed documents or Cosmos DB, and provides a response.
Overall, this serverless and automated system streamlines the entire workflow, minimizing manual effort while enabling intelligent, real time interaction with personalized content.

---

## 🛠️ Tech Stack

- **Backend**: Flask (Python)  
- **Frontend**: JavaScript  
- **AI/ML**: Azure OpenAI, Azure AI Search  
- **Cloud Services**: Azure Functions, Azure Cosmos DB, Azure Blob Storage  
- **Automation & Tools**: Azure Function Triggers, Notion API  

For more details, see the Backend and Frontend setup instructions linked below.

---

## 📺 Demo Video

<a href="https://youtu.be/NqOpKgq7Iak" target="_blank">
  <img src="https://img.youtube.com/vi/NqOpKgq7Iak/0.jpg" width="800" alt="Watch the demo video"/>
</a>

**👉 Click the image to watch the demo.**

---

## 🎮 How to Use

1. Clone the repository and set up your environment.  
2. Follow the setup guides:  
   - [Backend Setup Instructions](https://github.com/NAry-Byun/CWB_Hackathon-2025/blob/main/backend/readme.md)  
   - [Frontend Setup Instructions](https://github.com/NAry-Byun/CWB_Hackathon-2025/blob/main/frontend/readme.md)  
3. Upload or link documents, notes, or blogs scraped from the web, and save them to Azure Blob Storage.  
4. Ask questions and receive intelligent, context-aware answers.  
5. Explore automation features for smarter workflows.

---

## ✨ Features

- ✅ Speech-to-text transcription  
- ✅ Contextual answers from your uploaded data, Notion, and blog content  
- ✅ Seamless Notion integration (read/write)  
- ✅ Flashcards, quizzes, and summaries for enhanced learning  
- ✅ Vector search for intelligent content retrieval


---

## 📌 Key Takeaways

- Enables deep learning through AI-enhanced content interaction  
- Improves productivity with Notion integration  
- Supports intelligent automation pipelines using Azure  
- Builds prompt engineering and debugging skills for future workflows

---

## 📁 Resources

I attended the **Cognizant AI for Impact: APJ GenAI Skills Program 2025 – Prompt Engineering Workshop** and learned how to effectively use AI prompting to extract insights.  
The methods taught in that session were applied in Gomm AI to enhance debugging and user interaction.

![Workshop 1](https://github.com/NAry-Byun/CWB_Hackathon-2025/blob/main/frontend/src/imag/workshop1.jpg?raw=true)  
![Workshop 2](https://github.com/NAry-Byun/CWB_Hackathon-2025/blob/main/frontend/src/imag/workshop2.jpg?raw=true)
