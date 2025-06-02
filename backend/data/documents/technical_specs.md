# Technical Specifications

## API Endpoints
- `/api/chat/chat` - Enhanced chat with document search
- `/api/chat/simple` - Simple chat without context
- `/api/documents/upload` - Document upload and processing
- `/api/training/start` - Start comprehensive training
- `/health` - Service health check

## Environment Variables Required
- AZURE_OPENAI_API_KEY
- AZURE_OPENAI_ENDPOINT
- AZURE_OPENAI_DEPLOYMENT_NAME
- AZURE_OPENAI_EMBEDDING_DEPLOYMENT

## Supported File Formats
- Text files (.txt)
- Markdown (.md) 
- JSON (.json)
- CSV (.csv)
- Python (.py)
- JavaScript (.js)
- HTML (.html)
"""