

## 🛠️ Backend Instructions



---

### ⚙️ How to Set Up

1. Install required dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Run the Flask server:

   ```bash
   python app.py
   ```

---

### 🔑 Key Backend Features

**Routes:**

* `/notion`: Handles Notion API interactions
* `/chat`: Processes AI chat prompts and responses
* `/document`: Manages document uploads and parsing

**Services:**

* `cosmos_service.py`: Manages communication with Azure Cosmos DB
* `openai_service.py`: Handles interaction with Azure OpenAI


---

### ⚡ Azure Function Trigger

The original concept was implemented using a local Flask server. To automate the workflow and improve scalability, it was migrated to a serverless architecture using an Azure Function Trigger. This function is automatically invoked whenever a document is uploaded to Azure Blob Storage. It processes the file, extracts key information, and stores the structured data in Azure Cosmos DB. This approach reduces manual effort and simplifies the overall system architecture.

![Azure Trigger Flow](https://github.com/NAry-Byun/CWB_Hackathon-2025/blob/develop/frontend/src/imag/rahul_trigger.png?raw=true)

---

### 🧠 Notion API Integration

I initially attempted to integrate **Notion MCP**, but it was not available at the time.
As an alternative, I used the **Python Notion API client** (`notion-client` library).
In the future, I plan to integrate more advanced features using **OpenAI models**.
While working with the Notion API, I encountered several debugging challenges and had to ensure each endpoint existed and functioned correctly.

---

### 🔗 Resources

* [Notion MCP Server (GitHub)](https://github.com/makenotion/notion-mcp-server)
* [notion-client (PyPI)](https://pypi.org/project/notion-client/)
* [Notion API Overview](https://developers.notion.com/docs/getting-started)
* [Azure Functions triggers and bindings concepts](https://learn.microsoft.com/en-us/azure/azure-functions/functions-triggers-bindings?tabs=isolated-process%2Cnode-v4%2Cpython-v2&pivots=programming-language-csharp)


