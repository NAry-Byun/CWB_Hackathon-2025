import os
import json
import asyncio
import logging
from pathlib import Path
import subprocess
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BackendSetup:
    """Setup script for AI Training Backend"""
    
    def __init__(self):
        self.project_root = Path.cwd()
        self.config_dir = self.project_root / "config"
        self.data_dir = self.project_root / "data"
        self.logs_dir = self.project_root / "logs"
    
    def create_directory_structure(self):
        """Create necessary directories"""
        directories = [
            self.config_dir,
            self.data_dir / "documents",
            self.data_dir / "exports", 
            self.data_dir / "backups",
            self.logs_dir,
            self.project_root / "services"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created directory: {directory}")
    
    def create_env_template(self):
        """Create .env template file"""
        env_template = """# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT=https://your-openai-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-openai-api-key

# Azure Cosmos DB Configuration  
COSMOS_DB_ENDPOINT=https://your-cosmos-account.documents.azure.com:443/
COSMOS_DB_KEY=your-cosmos-db-key

# Optional: Azure Storage
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=...

# Optional: Notion Integration
NOTION_API_KEY=secret_your_notion_integration_token
NOTION_VERSION=2022-06-28

# Application Settings
LOG_LEVEL=INFO
"""
        
        env_file = self.project_root / ".env.template"
        with open(env_file, 'w') as f:
            f.write(env_template)
        
        logger.info(f"Created environment template: {env_file}")
        logger.info("Please copy .env.template to .env and update with your credentials")
    
    def create_default_config(self):
        """Create default configuration file"""
        config = {
            "training_config": {
                "description": "Backend AI Training Configuration",
                "version": "1.0",
                "azure_openai": {
                    "endpoint": "${AZURE_OPENAI_ENDPOINT}",
                    "api_key": "${AZURE_OPENAI_API_KEY}",
                    "embedding_model": "text-embedding-3-small",
                    "chat_model": "gpt-4",
                    "embedding_dimensions": 1536
                },
                "cosmos_db": {
                    "endpoint": "${COSMOS_DB_ENDPOINT}",
                    "key": "${COSMOS_DB_KEY}",
                    "database_name": "ai_training_backend"
                },
                "training_sources": {
                    "directories": [
                        {
                            "path": "./data/documents",
                            "recursive": True,
                            "batch_size": 5,
                            "source_type": "document",
                            "enabled": True
                        }
                    ],
                    "azure_storage": [],
                    "notion": {
                        "database_ids": [],
                        "page_ids": [],
                        "enabled": False
                    },
                    "web_scraping": {
                        "urls": [],
                        "sitemaps": [],
                        "enabled": False
                    }
                },
                "training_settings": {
                    "chunk_size": 1000,
                    "chunk_overlap": 200,
                    "embedding_batch_size": 10,
                    "max_concurrent_files": 5,
                    "rate_limit_rpm": 3000
                }
            }
        }
        
        config_file = self.config_dir / "training_config.json"
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        logger.info(f"Created default configuration: {config_file}")
    
    def create_sample_documents(self):
        """Create sample documents for testing"""
        sample_docs = [
            ("machine_learning.txt", """
Machine Learning Overview

Machine learning is a method of data analysis that automates analytical model building. 
It is a branch of artificial intelligence (AI) based on the idea that systems can learn 
from data, identify patterns and make decisions with minimal human intervention.

Key Concepts:
- Supervised Learning: Learning with labeled examples
- Unsupervised Learning: Finding patterns in unlabeled data  
- Reinforcement Learning: Learning through interaction with environment
- Deep Learning: Neural networks with multiple layers

Applications include image recognition, natural language processing, 
recommendation systems, and autonomous vehicles.
            """),
            ("ai_concepts.txt", """
Artificial Intelligence Concepts

Artificial Intelligence (AI) refers to the simulation of human intelligence 
in machines that are programmed to think and learn like humans.

Types of AI:
1. Narrow AI: Designed for specific tasks
2. General AI: Human-level intelligence across domains
3. Superintelligence: Exceeds human cognitive abilities

Key technologies:
- Natural Language Processing (NLP)
- Computer Vision
- Robotics
- Expert Systems
- Machine Learning

AI is transforming industries including healthcare, finance, 
transportation, and education.
            """),
            ("deep_learning.md", """
# Deep Learning Guide

Deep learning is a subset of machine learning that uses neural networks 
with multiple layers (hence "deep") to model and understand complex patterns.

## Neural Network Architectures

### Feedforward Networks
- Basic neural network structure
- Information flows in one direction
- Used for classification and regression

### Convolutional Neural Networks (CNNs)
- Specialized for image processing
- Uses convolution operations
- Applications: image recognition, computer vision

### Recurrent Neural Networks (RNNs)
- Designed for sequential data
- Has memory of previous inputs
- Applications: language modeling, time series

### Transformer Architecture
- Attention mechanism
- Parallel processing
- Applications: BERT, GPT, language translation

## Training Process
1. Forward propagation
2. Loss calculation  
3. Backpropagation
4. Parameter updates
            """)
        ]
        
        docs_dir = self.data_dir / "documents"
        for filename, content in sample_docs:
            doc_file = docs_dir / filename
            with open(doc_file, 'w') as f:
                f.write(content.strip())
            logger.info(f"Created sample document: {doc_file}")
    
    def create_startup_scripts(self):
        """Create startup scripts"""
        # CLI startup script
        cli_script = """#!/bin/bash
# start_training.sh - CLI Training Script

echo "AI Training Backend - CLI Mode"
echo "=============================="

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Check environment
if [ ! -f ".env" ]; then
    echo "Warning: .env file not found. Please create from .env.template"
    exit 1
fi

# Initialize infrastructure
echo "Initializing infrastructure..."
python main_training.py --init

echo "Setup complete! You can now run training commands:"
echo "  python main_training.py --train-local ./data/documents"
echo "  python main_training.py --stats"
echo "  python main_training.py --search 'machine learning'"
"""
        
        cli_file = self.project_root / "start_training.sh"
        with open(cli_file, 'w') as f:
            f.write(cli_script)
        
        # Make executable on Unix systems
        if os.name != 'nt':
            os.chmod(cli_file, 0o755)
        
        # API startup script
        api_script = """#!/bin/bash
# start_api.sh - API Server Script

echo "AI Training Backend - API Mode"
echo "=============================="

# Activate virtual environment
source venv/bin/activate

# Check environment
if [ ! -f ".env" ]; then
    echo "Warning: .env file not found. Please create from .env.template"
    exit 1
fi

# Start API server
echo "Starting API server..."
echo "API will be available at: http://localhost:8000"
echo "Health check: http://localhost:8000/health"
echo "API docs: http://localhost:8000/docs"

python backend_api.py
"""
        
        api_file = self.project_root / "start_api.sh"
        with open(api_file, 'w') as f:
            f.write(api_script)
        
        if os.name != 'nt':
            os.chmod(api_file, 0o755)
        
        # Windows batch files
        if os.name == 'nt':
            cli_bat = """@echo off
REM start_training.bat - CLI Training Script for Windows

echo AI Training Backend - CLI Mode
echo ==============================

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\\Scripts\\activate.bat

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

REM Check environment
if not exist ".env" (
    echo Warning: .env file not found. Please create from .env.template
    pause
    exit /b 1
)

REM Initialize infrastructure
echo Initializing infrastructure...
python main_training.py --init

echo Setup complete! You can now run training commands:
echo   python main_training.py --train-local ./data/documents
echo   python main_training.py --stats
pause
"""
            
            with open(self.project_root / "start_training.bat", 'w') as f:
                f.write(cli_bat)
            
            api_bat = """@echo off
REM start_api.bat - API Server Script for Windows

echo AI Training Backend - API Mode
echo ==============================

REM Activate virtual environment  
call venv\\Scripts\\activate.bat

REM Check environment
if not exist ".env" (
    echo Warning: .env file not found. Please create from .env.template
    pause
    exit /b 1
)

REM Start API server
echo Starting API server...
echo API will be available at: http://localhost:8000
echo Health check: http://localhost:8000/health
echo API docs: http://localhost:8000/docs

python backend_api.py
pause
"""
            
            with open(self.project_root / "start_api.bat", 'w') as f:
                f.write(api_bat)
        
        logger.info("Created startup scripts")
    
    def create_readme(self):
        """Create README file"""
        readme_content = """# AI Training Backend

Backend-only AI training system using Cosmos DB, Azure Storage, Notion, and Web Scraping.

## Quick Start

1. **Setup Environment:**
   ```bash
   cp .env.template .env
   # Edit .env with your Azure credentials
   ```

2. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Initialize Infrastructure:**
   ```bash
   python main_training.py --init
   ```

4. **Start Training:**
   ```bash
   # CLI Mode
   python main_training.py --train-local ./data/documents
   
   # API Mode  
   python backend_api.py
   ```

## Usage Examples

### CLI Training
```bash
# Train from local files
python main_training.py --train-local ./data/documents

# Train from Azure Storage
python main_training.py --train-storage my-container

# Train from web URLs
python main_training.py --train-web https://example.com/blog

# Get statistics
python main_training.py --stats
```

### API Training
```bash
# Start API server
python backend_api.py

# Train via API
curl -X POST "http://localhost:8000/train" \\
  -H "Content-Type: application/json" \\
  -d '{"source_type": "local", "path": "./data/documents"}'
```

## Configuration

Edit `config/training_config.json` to customize:
- Training sources (local, Azure Storage, Notion, web)
- Embedding settings
- Batch sizes and performance tuning

## Features

- ✅ Multi-source training (Local, Azure Storage, Notion, Web)
- ✅ Vector embeddings with Azure OpenAI
- ✅ RESTful API for integration
- ✅ Batch processing and rate limiting
- ✅ Smart caching and deduplication
- ✅ Comprehensive logging and error handling

For detailed usage, see the usage guide documentation.
"""
        
        readme_file = self.project_root / "README.md"
        with open(readme_file, 'w') as f:
            f.write(readme_content)
        
        logger.info(f"Created README: {readme_file}")
    
    def run_setup(self):
        """Run complete setup"""
        logger.info("Starting AI Training Backend setup...")
        
        self.create_directory_structure()
        self.create_env_template()
        self.create_default_config()
        self.create_sample_documents()
        self.create_startup_scripts()
        self.create_readme()
        
        logger.info("Setup completed successfully!")
        print(f"""
🎉 AI Training Backend Setup Complete!

Next steps:
1. Copy .env.template to .env and add your Azure credentials
2. Install dependencies: pip install -r requirements.txt
3. Initialize: python main_training.py --init
4. Start training: python main_training.py --train-local ./data/documents

Or start the API server: python backend_api.py

Documentation and examples are in the README.md file.
""")

if __name__ == "__main__":
    setup = BackendSetup()
    setup.run_setup()