import json
import logging
import asyncio
import os
from datetime import datetime
from typing import Dict, Any

import azure.functions as func
from azure.storage.blob import BlobServiceClient
import requests

# Import your training backend (needs to be deployed with the function)
from main_training import AITrainingBackend

app = func.FunctionApp()

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global backend instance
backend: AITrainingBackend = None

async def get_backend():
    """Get or initialize backend instance"""
    global backend
    if backend is None:
        backend = AITrainingBackend()
        await backend.initialize_services()
    return backend

@app.timer_trigger(schedule="0 0 2 * * *", arg_name="timer", run_on_startup=False)
async def daily_training_trigger(timer: func.TimerRequest) -> None:
    """
    Daily training trigger - runs every day at 2 AM UTC
    Schedule format: "0 0 2 * * *" (seconds minutes hours day month dayofweek)
    """
    logger.info("Daily training trigger started")
    
    try:
        training_backend = await get_backend()
        
        # Run comprehensive training from all configured sources
        result = await training_backend.run_comprehensive_training()
        
        # Log results
        summary = result.get('summary', {})
        logger.info(f"Daily training completed: {summary.get('totalDocuments', 0)} documents processed")
        
        # Send notification (optional)
        await send_notification(
            "Daily Training Completed",
            f"Processed {summary.get('totalDocuments', 0)} documents from {summary.get('totalSources', 0)} sources"
        )
        
    except Exception as e:
        logger.error(f"Daily training failed: {e}")
        await send_notification("Daily Training Failed", str(e), level="error")

@app.timer_trigger(schedule="0 0 3 * * 0", arg_name="timer", run_on_startup=False)  
async def weekly_comprehensive_training(timer: func.TimerRequest) -> None:
    """
    Weekly comprehensive training - runs every Sunday at 3 AM UTC
    """
    logger.info("Weekly comprehensive training trigger started")
    
    try:
        training_backend = await get_backend()
        
        # Run more intensive training with higher batch sizes
        result = await training_backend.run_comprehensive_training()
        
        # Get detailed statistics
        stats = await training_backend.get_training_statistics()
        
        # Log detailed results
        kb_stats = stats.get('knowledgeBase', {})
        logger.info(f"Weekly training completed:")
        logger.info(f"  Total documents: {kb_stats.get('totalDocuments', 0)}")
        logger.info(f"  Source distribution: {kb_stats.get('sourceDistribution', {})}")
        
        # Send detailed notification
        await send_notification(
            "Weekly Training Completed",
            f"Knowledge base now contains {kb_stats.get('totalDocuments', 0)} documents"
        )
        
    except Exception as e:
        logger.error(f"Weekly training failed: {e}")
        await send_notification("Weekly Training Failed", str(e), level="error")

@app.blob_trigger(arg_name="blob", path="training-documents/{name}", connection="AzureWebJobsStorage")
async def blob_upload_trigger(blob: func.InputStream) -> None:
    """
    Blob trigger - automatically processes new files uploaded to Azure Storage
    Triggers when files are added to 'training-documents' container
    """
    logger.info(f"Blob trigger activated for: {blob.name}")
    
    try:
        # Get blob properties
        blob_name = blob.name
        blob_content = blob.read().decode('utf-8')
        
        training_backend = await get_backend()
        
        # Add content directly to knowledge base
        document_ids = await training_backend.add_manual_content(
            content=blob_content,
            source_type="azure_blob_upload",
            metadata={
                "blob_name": blob_name,
                "upload_time": datetime.utcnow().isoformat(),
                "file_size": len(blob_content)
            }
        )
        
        logger.info(f"Processed uploaded blob {blob_name}: {len(document_ids)} documents created")
        
        # Send notification
        await send_notification(
            "New File Processed",
            f"Processed {blob_name}: {len(document_ids)} documents added to knowledge base"
        )
        
    except Exception as e:
        logger.error(f"Blob trigger failed for {blob.name}: {e}")
        await send_notification("Blob Processing Failed", f"{blob.name}: {str(e)}", level="error")

@app.function_name(name="HttpTrainingTrigger")
@app.route(route="train", methods=["POST"])
async def http_training_trigger(req: func.HttpRequest) -> func.HttpResponse:
    """
    HTTP trigger for webhook-based training
    Allows external systems to trigger training via HTTP POST
    """
    logger.info("HTTP training trigger received")
    
    try:
        # Parse request body
        req_body = req.get_json()
        
        if not req_body:
            return func.HttpResponse(
                json.dumps({"error": "Request body is required"}),
                status_code=400,
                mimetype="application/json"
            )
        
        training_backend = await get_backend()
        
        # Extract training parameters
        source_type = req_body.get("source_type", "all")
        
        if source_type == "local":
            path = req_body.get("path", "./data/documents")
            result = await training_backend.train_from_local_files(path)
            
        elif source_type == "azure_storage":
            container = req_body.get("container_name")
            if not container:
                return func.HttpResponse(
                    json.dumps({"error": "container_name is required for azure_storage"}),
                    status_code=400,
                    mimetype="application/json"
                )
            result = await training_backend.train_from_azure_storage(container)
            
        elif source_type == "notion":
            database_ids = req_body.get("database_ids")
            page_ids = req_body.get("page_ids")
            result = await training_backend.train_from_notion(database_ids, page_ids)
            
        elif source_type == "web":
            urls = req_body.get("urls")
            if not urls:
                return func.HttpResponse(
                    json.dumps({"error": "urls are required for web training"}),
                    status_code=400,
                    mimetype="application/json"
                )
            result = await training_backend.train_from_web_urls(urls)
            
        elif source_type == "all":
            result = await training_backend.run_comprehensive_training()
            
        else:
            return func.HttpResponse(
                json.dumps({"error": f"Unknown source_type: {source_type}"}),
                status_code=400,
                mimetype="application/json"
            )
        
        # Return success response
        response_data = {
            "status": "success",
            "message": "Training completed successfully",
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(f"HTTP training completed: {result}")
        
        return func.HttpResponse(
            json.dumps(response_data),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logger.error(f"HTTP training trigger failed: {e}")
        
        error_response = {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return func.HttpResponse(
            json.dumps(error_response),
            status_code=500,
            mimetype="application/json"
        )

@app.function_name(name="EventGridTrigger")
@app.event_grid_trigger(arg_name="event")
async def event_grid_trigger(event: func.EventGridEvent) -> None:
    """
    Event Grid trigger - responds to Azure Event Grid events
    Can be used for various Azure service events (Storage, Cosmos DB, etc.)
    """
    logger.info(f"Event Grid trigger received: {event.event_type}")
    
    try:
        event_data = event.get_json()
        event_type = event.event_type
        
        training_backend = await get_backend()
        
        # Handle different event types
        if event_type == "Microsoft.Storage.BlobCreated":
            # New blob created in storage
            blob_url = event_data.get("url", "")
            logger.info(f"New blob created: {blob_url}")
            
            # Trigger storage training for the specific container
            container_name = extract_container_from_url(blob_url)
            if container_name:
                result = await training_backend.train_from_azure_storage(container_name)
                await send_notification(
                    "Storage Event Training",
                    f"Processed new blob in {container_name}: {result.get('totalDocuments', 0)} documents"
                )
        
        elif event_type == "Microsoft.Web.AppUpdated":
            # Website updated - could trigger web scraping
            site_url = event_data.get("url", "")
            if site_url:
                result = await training_backend.train_from_website_sitemap(site_url)
                await send_notification(
                    "Website Update Training",
                    f"Website updated, reprocessed: {result.get('documents_created', 0)} documents"
                )
        
        elif event_type == "Custom.NotionUpdate":
            # Custom event for Notion updates
            result = await training_backend.train_from_notion()
            await send_notification(
                "Notion Update Training",
                f"Notion updated: {result.get('totalDocuments', 0)} documents processed"
            )
        
        else:
            logger.info(f"Unhandled event type: {event_type}")
        
    except Exception as e:
        logger.error(f"Event Grid trigger failed: {e}")
        await send_notification("Event Grid Trigger Failed", str(e), level="error")

@app.function_name(name="CosmosDBTrigger")
@app.cosmos_db_trigger(arg_name="documents", connection="CosmosDBConnection",
                      database_name="ai_training_backend", container_name="feedback")
async def cosmos_feedback_trigger(documents: func.DocumentList) -> None:
    """
    Cosmos DB trigger - responds to changes in feedback collection
    Automatically retrains when new feedback is received
    """
    logger.info(f"Cosmos DB trigger activated: {len(documents)} documents changed")
    
    try:
        training_backend = await get_backend()
        
        # Process feedback documents
        feedback_count = 0
        correction_count = 0
        
        for doc in documents:
            doc_dict = doc.to_dict()
            feedback_type = doc_dict.get("feedbackType", "")
            
            feedback_count += 1
            
            # If this is a correction, we might want to retrain
            if feedback_type == "correction":
                correction_count += 1
        
        logger.info(f"Processed {feedback_count} feedback items ({correction_count} corrections)")
        
        # If we have enough corrections, trigger retraining
        if correction_count >= 5:  # Threshold for retraining
            logger.info("Triggering retraining due to feedback corrections")
            result = await training_backend.run_comprehensive_training()
            
            await send_notification(
                "Feedback-Triggered Retraining",
                f"Retrained due to {correction_count} corrections: {result.get('summary', {}).get('totalDocuments', 0)} documents"
            )
        
    except Exception as e:
        logger.error(f"Cosmos DB trigger failed: {e}")

@app.function_name(name="ManualTrainingTrigger")
@app.route(route="manual-train", methods=["POST"])
async def manual_training_trigger(req: func.HttpRequest) -> func.HttpResponse:
    """
    Manual training trigger with content in request body
    Allows adding training content directly via HTTP request
    """
    logger.info("Manual training trigger received")
    
    try:
        req_body = req.get_json()
        
        if not req_body or "content" not in req_body:
            return func.HttpResponse(
                json.dumps({"error": "Content is required in request body"}),
                status_code=400,
                mimetype="application/json"
            )
        
        training_backend = await get_backend()
        
        # Extract parameters
        content = req_body["content"]
        source_type = req_body.get("source_type", "manual")
        metadata = req_body.get("metadata", {})
        
        # Add timestamp to metadata
        metadata["submitted_at"] = datetime.utcnow().isoformat()
        metadata["source"] = "manual_http_trigger"
        
        # Add content to knowledge base
        document_ids = await training_backend.add_manual_content(
            content=content,
            source_type=source_type,
            metadata=metadata
        )
        
        response_data = {
            "status": "success",
            "message": f"Content added successfully: {len(document_ids)} documents created",
            "document_ids": document_ids,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Manual content added: {len(document_ids)} documents")
        
        return func.HttpResponse(
            json.dumps(response_data),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logger.error(f"Manual training trigger failed: {e}")
        
        return func.HttpResponse(
            json.dumps({
                "status": "error",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }),
            status_code=500,
            mimetype="application/json"
        )

# Utility functions
async def send_notification(subject: str, message: str, level: str = "info") -> None:
    """Send notification (customize based on your notification system)"""
    try:
        # Example: Send to Teams webhook, email, or logging service
        webhook_url = os.getenv("TEAMS_WEBHOOK_URL")
        
        if webhook_url:
            notification_data = {
                "text": f"**{subject}**\n\n{message}",
                "themeColor": "00FF00" if level == "info" else "FF0000"
            }
            
            response = requests.post(webhook_url, json=notification_data)
            logger.info(f"Notification sent: {subject}")
        else:
            logger.info(f"Notification: {subject} - {message}")
            
    except Exception as e:
        logger.error(f"Failed to send notification: {e}")

def extract_container_from_url(blob_url: str) -> str:
    """Extract container name from blob URL"""
    try:
        # Parse URL to extract container name
        # Example: https://account.blob.core.windows.net/container/blob
        parts = blob_url.split('/')
        if len(parts) >= 4:
            return parts[3]  # Container name
    except Exception:
        pass
    return ""

# Health check endpoint
@app.function_name(name="HealthCheck")
@app.route(route="health", methods=["GET"])
async def health_check(req: func.HttpRequest) -> func.HttpResponse:
    """Health check endpoint for the Function App"""
    try:
        # Try to initialize backend to test connectivity
        training_backend = await get_backend()
        stats = await training_backend.get_training_statistics()
        
        health_data = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "cosmos_db": "connected",
                "azure_openai": "connected",
                "training_backend": "ready"
            },
            "knowledge_base": {
                "total_documents": stats.get("knowledgeBase", {}).get("totalDocuments", 0)
            }
        }
        
        return func.HttpResponse(
            json.dumps(health_data),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        error_data = {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }
        
        return func.HttpResponse(
            json.dumps(error_data),
            status_code=500,
            mimetype="application/json"
        )