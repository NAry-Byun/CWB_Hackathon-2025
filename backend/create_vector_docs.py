# create_vector_docs.py - Create new documents with embeddings from your course data

import asyncio
import os
import logging
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

from services.cosmos_service import CosmosVectorService
from services.azure_openai_service import AzureOpenAIService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VectorDocumentCreator:
    """Create vector-searchable documents from course data"""
    
    def __init__(self):
        self.cosmos_service = CosmosVectorService()
        self.openai_service = AzureOpenAIService()
    
    async def create_sample_vector_documents(self):
        """Create sample documents with embeddings for testing"""
        await self.cosmos_service.initialize_database()
        
        # Sample course documents based on your data structure
        sample_courses = [
            {
                "title": "Introduction to Machine Learning",
                "description": "Learn the fundamentals of machine learning including supervised and unsupervised learning, neural networks, and practical applications in AI.",
                "category": "ai-courses",
                "difficulty": "beginner",
                "modules": 8,
                "duration_hours": 40
            },
            {
                "title": "Deep Learning with Neural Networks", 
                "description": "Advanced course covering deep neural networks, convolutional networks, RNNs, and transformer architectures for AI applications.",
                "category": "ai-courses",
                "difficulty": "advanced", 
                "modules": 12,
                "duration_hours": 60
            },
            {
                "title": "Natural Language Processing Fundamentals",
                "description": "Explore NLP techniques including tokenization, sentiment analysis, language models, and text generation using modern AI.",
                "category": "ai-courses",
                "difficulty": "intermediate",
                "modules": 10,
                "duration_hours": 50
            },
            {
                "title": "Computer Vision with AI",
                "description": "Learn image recognition, object detection, and computer vision applications using deep learning and AI technologies.",
                "category": "ai-courses", 
                "difficulty": "intermediate",
                "modules": 9,
                "duration_hours": 45
            },
            {
                "title": "AI Ethics and Responsible AI Development",
                "description": "Understanding ethical considerations in AI development, bias mitigation, and responsible deployment of AI systems.",
                "category": "ai-courses",
                "difficulty": "beginner",
                "modules": 6,
                "duration_hours": 25
            }
        ]
        
        created_count = 0
        
        for i, course in enumerate(sample_courses):
            try:
                # Create text for embedding
                embedding_text = f"{course['title']}. {course['description']} Category: {course['category']}. Difficulty: {course['difficulty']}. Duration: {course['duration_hours']} hours."
                
                # Generate embedding
                embedding = await self.openai_service.generate_embeddings(embedding_text)
                
                if embedding:
                    # Create document with vector
                    doc = {
                        "id": f"course_{i+1}_{course['title'].lower().replace(' ', '_')}",
                        "file_name": f"course_{i+1}",
                        "chunk_text": embedding_text,
                        "chunk_index": 0,
                        "embedding": embedding,
                        "metadata": {
                            "source_type": "course_catalog",
                            "title": course['title'],
                            "description": course['description'],
                            "category": course['category'],
                            "difficulty": course['difficulty'],
                            "modules": course['modules'],
                            "duration_hours": course['duration_hours'],
                            "created_at": "2025-06-01T18:30:00Z"
                        }
                    }
                    
                    # Store in Cosmos DB
                    await self.cosmos_service.container.create_item(body=doc)
                    created_count += 1
                    logger.info(f"✅ Created vector document: {course['title']}")
                
            except Exception as e:
                logger.error(f"❌ Failed to create document for {course['title']}: {e}")
                continue
        
        logger.info(f"🎉 Created {created_count} vector-searchable documents!")
        return created_count

    async def test_vector_search(self):
        """Test vector search with a sample query"""
        try:
            # Test search
            test_query = "machine learning neural networks deep learning"
            embedding = await self.openai_service.generate_embeddings(test_query)
            
            if embedding:
                results = await self.cosmos_service.search_similar_chunks(
                    query_embedding=embedding,
                    limit=3,
                    similarity_threshold=0.1
                )
                
                logger.info(f"🔍 Test search for '{test_query}' found {len(results)} results:")
                for i, result in enumerate(results, 1):
                    title = result.get('metadata', {}).get('title', 'Unknown')
                    similarity = result.get('similarity', 0)
                    logger.info(f"  {i}. {title} (similarity: {similarity:.3f})")
                
                return results
            
        except Exception as e:
            logger.error(f"❌ Test search failed: {e}")
            return []

async def main():
    """Create sample vector documents and test search"""
    creator = VectorDocumentCreator()
    
    print("🔄 Creating sample vector documents...")
    await creator.create_sample_vector_documents()
    
    print("\n🔍 Testing vector search...")
    await creator.test_vector_search()
    
    print("\n✅ Done! Your Cosmos DB now has vector-searchable documents.")

if __name__ == "__main__":
    asyncio.run(main())