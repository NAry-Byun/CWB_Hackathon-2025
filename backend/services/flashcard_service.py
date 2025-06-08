# services/flashcard_service.py - COMPLETE FIXED VERSION

import os
import logging
import uuid
import json
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import time

logger = logging.getLogger(__name__)

class FlashCardService:
    """Complete Enhanced Flash Card Service with FIXED AI-powered content generation"""

    def __init__(self):
        """Initialize Flash Card service with file-based storage"""
        self.data_dir = os.path.join(os.getcwd(), 'data', 'flashcards')
        self.cards_file = os.path.join(self.data_dir, 'flashcards.json')
        self.progress_file = os.path.join(self.data_dir, 'progress.json')
        
        # Create directory if it doesn't exist
        os.makedirs(self.data_dir, exist_ok=True)
        
        self.openai_service = None
        self._initialize_files()
        
        logger.info("🧠 FlashCardService initialized (file-based storage)")

    def _initialize_files(self):
        """Initialize JSON files if they don't exist"""
        try:
            if not os.path.exists(self.cards_file):
                with open(self.cards_file, 'w') as f:
                    json.dump({}, f)
            
            if not os.path.exists(self.progress_file):
                with open(self.progress_file, 'w') as f:
                    json.dump({}, f)
                    
            logger.info("✅ FlashCard files initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize files: {e}")

    def set_openai_service(self, openai_service):
        """Inject OpenAI service for AI enhancements"""
        self.openai_service = openai_service
        logger.info("✅ OpenAI service injected into FlashCardService")

    def _load_cards(self) -> Dict:
        """Load flashcards from file"""
        try:
            with open(self.cards_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"❌ Failed to load cards: {e}")
            return {}

    def _save_cards(self, cards: Dict):
        """Save flashcards to file"""
        try:
            with open(self.cards_file, 'w') as f:
                json.dump(cards, f, indent=2)
        except Exception as e:
            logger.error(f"❌ Failed to save cards: {e}")

    def _load_progress(self) -> Dict:
        """Load progress from file"""
        try:
            with open(self.progress_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"❌ Failed to load progress: {e}")
            return {}

    def _save_progress(self, progress: Dict):
        """Save progress to file"""
        try:
            with open(self.progress_file, 'w') as f:
                json.dump(progress, f, indent=2)
        except Exception as e:
            logger.error(f"❌ Failed to save progress: {e}")

    async def _generate_ai_flashcard_content(self, user_question: str, ai_response: str, conversation_context: List[Dict] = None) -> Dict[str, Any]:
        """FIXED: Use AI to generate proper flashcard content from conversation"""
        if not self.openai_service:
            logger.warning("⚠️ OpenAI service not available, using smart extraction")
            return self._extract_smart_flashcard_content(user_question, ai_response)

        try:
            # FIXED: Much more direct and specific prompt
            prompt = f"""Extract the key educational concept from this AI response and create a study flashcard.

AI Response: {ai_response}

Create a flashcard with:
- FRONT: The main topic/concept (concise title, NOT a question)
- BACK: Key points in bullet format

Example format:
FRONT: "Business Plan Components"
BACK: "• Executive Summary: Company overview and mission\\n• Market Analysis: Target audience and competitors\\n• Financial Projections: Revenue and expense forecasts"

Now create the flashcard for the content above:

FRONT: """

            # Generate AI response
            ai_result = await self.openai_service.generate_response(
                user_message=prompt,
                context=[],
                document_chunks=[],
                notion_pages=[],
                max_tokens=200,
                temperature=0.1  # Low temperature for consistent formatting
            )

            # Extract content from AI response
            if isinstance(ai_result, dict):
                ai_text = ai_result.get("assistant_message", str(ai_result))
            else:
                ai_text = str(ai_result)

            logger.info(f"🤖 AI response for flashcard: {ai_text[:100]}...")

            # FIXED: Better parsing of AI response
            front, back = self._parse_ai_flashcard_response(ai_text)
            
            if front and back:
                logger.info("✅ AI generated flashcard content successfully")
                return {
                    "front": front.strip(),
                    "back": back.strip(),
                    "difficulty": self._assess_difficulty(back),
                    "tags": self._extract_smart_tags(ai_response),
                    "mnemonic": None,
                    "ai_enhanced": True
                }
            else:
                logger.warning("⚠️ AI response parsing failed, using smart extraction")
                return self._extract_smart_flashcard_content(user_question, ai_response)

        except Exception as e:
            logger.error(f"❌ AI flashcard generation failed: {e}")
            return self._extract_smart_flashcard_content(user_question, ai_response)

    def _parse_ai_flashcard_response(self, ai_text: str) -> tuple:
        """FIXED: Parse AI response to extract front and back content"""
        try:
            # Clean up the response
            ai_text = ai_text.strip()
            
            # Look for FRONT: and BACK: patterns
            front_match = re.search(r'FRONT:\s*["\']?([^"\'\n]+)["\']?', ai_text, re.IGNORECASE)
            back_match = re.search(r'BACK:\s*["\']?([^"\']+)["\']?', ai_text, re.IGNORECASE | re.DOTALL)
            
            if front_match and back_match:
                front = front_match.group(1).strip()
                back = back_match.group(1).strip()
                
                # Clean up the back content
                back = back.replace('\\n', '\n')
                
                # Remove any trailing quotes or unwanted characters
                front = re.sub(r'^["\']|["\']$', '', front)
                back = re.sub(r'^["\']|["\']$', '', back)
                
                return front, back
            
            # Alternative parsing: Look for quoted content after FRONT
            lines = ai_text.split('\n')
            front = None
            back_lines = []
            found_back = False
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                # Look for front content
                if 'front' in line.lower() and not front:
                    # Extract content after colon or quotes
                    match = re.search(r'[:]\s*["\']?([^"\'\n]+)["\']?', line)
                    if match:
                        front = match.group(1).strip()
                        continue
                
                # Look for back content
                if 'back' in line.lower():
                    found_back = True
                    # Check if back content is on the same line
                    match = re.search(r'[:]\s*["\']?([^"\']+)["\']?', line)
                    if match:
                        back_content = match.group(1).strip()
                        if back_content:
                            back_lines.append(back_content)
                    continue
                
                # Collect back content lines
                if found_back and line.startswith('•'):
                    back_lines.append(line)
            
            if front and back_lines:
                back = '\n'.join(back_lines)
                return front, back
            
            # Final fallback: Extract any quoted content
            quotes = re.findall(r'["\']([^"\']+)["\']', ai_text)
            if len(quotes) >= 2:
                return quotes[0], quotes[1]
            
            return None, None
            
        except Exception as e:
            logger.error(f"❌ Failed to parse AI response: {e}")
            return None, None

    def _extract_smart_flashcard_content(self, user_question: str, ai_response: str) -> Dict[str, Any]:
        """FIXED: Smart extraction when AI generation fails"""
        try:
            # Step 1: Extract main topic from AI response
            front = self._extract_main_topic(ai_response, user_question)
            
            # Step 2: Extract key points from AI response
            back = self._extract_key_points(ai_response)
            
            return {
                "front": front,
                "back": back,
                "difficulty": self._assess_difficulty(back),
                "tags": self._extract_smart_tags(ai_response),
                "mnemonic": None,
                "ai_enhanced": False
            }
            
        except Exception as e:
            logger.error(f"❌ Smart extraction failed: {e}")
            return self._fallback_extraction(user_question, ai_response)

    def _extract_main_topic(self, ai_response: str, user_question: str) -> str:
        """Extract the main topic/concept from the content"""
        try:
            # Look for topic patterns in AI response
            topic_patterns = [
                r'(?:about|for|of)\s+([A-Z][^.!?]*)',  # "about Business Plans"
                r'([A-Z][A-Za-z\s]+(?:Plan|Strategy|Process|Method|System|Analysis))',  # Business Plan, etc.
                r'(?:key|main|important)\s+([A-Za-z\s]+)',  # "key concepts"
                r'([A-Z][A-Za-z\s]+)\s+(?:include|are|consist)',  # "Components include"
            ]
            
            for pattern in topic_patterns:
                matches = re.findall(pattern, ai_response)
                if matches:
                    topic = matches[0].strip()
                    if len(topic) > 10 and len(topic) < 60:
                        return topic
            
            # Extract from user question if no good topic found
            if user_question:
                # Remove question words and clean up
                clean_question = user_question.lower()
                clean_question = re.sub(r'\b(what|how|why|when|where|can|could|would|should|do|does|is|are)\b', '', clean_question)
                clean_question = re.sub(r'\b(you|me|i|help|explain|tell|about)\b', '', clean_question)
                clean_question = clean_question.replace('?', '').strip()
                
                if clean_question:
                    # Capitalize and format
                    topic = ' '.join(word.capitalize() for word in clean_question.split())
                    if len(topic) > 5:
                        return topic[:60]  # Limit length
            
            # Final fallback
            return "Key Concept"
            
        except Exception as e:
            logger.error(f"❌ Topic extraction failed: {e}")
            return "Study Topic"

    def _extract_key_points(self, ai_response: str) -> str:
        """Extract and format key points from AI response"""
        try:
            # Look for existing bullet points
            bullet_points = []
            lines = ai_response.split('\n')
            
            for line in lines:
                line = line.strip()
                if re.match(r'^[•\-\*]\s+', line):
                    bullet_points.append(line)
                elif re.match(r'^\d+\.\s+', line):
                    # Convert numbered lists to bullet points
                    content = re.sub(r'^\d+\.\s+', '• ', line)
                    bullet_points.append(content)
            
            if bullet_points:
                return '\n'.join(bullet_points[:5])  # Max 5 points
            
            # If no bullet points, create them from sentences
            sentences = re.split(r'[.!?]+', ai_response)
            key_sentences = []
            
            for sentence in sentences:
                sentence = sentence.strip()
                if (len(sentence) > 20 and len(sentence) < 150 and 
                    not sentence.lower().startswith(('here', 'this', 'i', 'you', 'sure'))):
                    key_sentences.append(f"• {sentence}")
                    if len(key_sentences) >= 4:
                        break
            
            if key_sentences:
                return '\n'.join(key_sentences)
            
            # Final fallback: Use first part of response
            if len(ai_response) > 100:
                truncated = ai_response[:200].strip()
                if not truncated.endswith('.'):
                    truncated += "..."
                return f"• {truncated}"
            
            return f"• {ai_response.strip()}"
            
        except Exception as e:
            logger.error(f"❌ Key points extraction failed: {e}")
            return f"• {ai_response[:100]}..."

    def _assess_difficulty(self, content: str) -> int:
        """Assess difficulty based on content complexity"""
        try:
            # Simple heuristics for difficulty
            difficulty = 3  # Default medium
            
            word_count = len(content.split())
            line_count = len(content.split('\n'))
            
            # Adjust based on length and complexity
            if word_count < 20:
                difficulty = 2  # Easy
            elif word_count > 60:
                difficulty = 4  # Hard
            
            # Check for complex terms
            complex_indicators = ['strategy', 'analysis', 'implementation', 'optimization', 'methodology']
            if any(term in content.lower() for term in complex_indicators):
                difficulty = min(difficulty + 1, 5)
            
            return difficulty
            
        except Exception:
            return 3

    def _extract_smart_tags(self, text: str) -> List[str]:
        """Extract intelligent tags from text"""
        tags = []
        text_lower = text.lower()
        
        # Business and strategy
        if any(word in text_lower for word in ['business', 'plan', 'strategy', 'company', 'market', 'revenue', 'profit']):
            tags.append("business")
        
        # Technology
        if any(word in text_lower for word in ['technology', 'software', 'computer', 'digital', 'ai', 'algorithm']):
            tags.append("technology")
        
        # Science
        if any(word in text_lower for word in ['science', 'research', 'study', 'analysis', 'data']):
            tags.append("science")
        
        # Finance
        if any(word in text_lower for word in ['financial', 'budget', 'cost', 'investment', 'money']):
            tags.append("finance")
        
        # Marketing
        if any(word in text_lower for word in ['marketing', 'customer', 'campaign', 'brand', 'promotion']):
            tags.append("marketing")
        
        # Management
        if any(word in text_lower for word in ['management', 'team', 'project', 'leadership', 'organization']):
            tags.append("management")
        
        if not tags:
            tags = ["general"]
        
        return tags[:3]  # Max 3 tags

    def _fallback_extraction(self, user_question: str, ai_response: str) -> Dict[str, Any]:
        """Final fallback extraction method"""
        return {
            "front": user_question[:60] if user_question else "Study Topic",
            "back": ai_response[:300] + "..." if len(ai_response) > 300 else ai_response,
            "difficulty": 3,
            "tags": ["general"],
            "mnemonic": None,
            "ai_enhanced": False
        }

    def create_flashcard_from_conversation_sync(
        self,
        user_id: str,
        question: str,
        answer: str,
        conversation_context: List[Dict] = None
    ) -> Dict[str, Any]:
        """Create a flashcard from a conversation Q&A - SYNCHRONOUS with FIXED AI enhancement"""
        try:
            # Generate unique flashcard ID
            flashcard_id = str(uuid.uuid4())
            
            # FIXED: Use improved AI content generation
            if self.openai_service:
                import asyncio
                import concurrent.futures
                
                try:
                    # Handle async properly
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            future = executor.submit(
                                asyncio.run, 
                                self._generate_ai_flashcard_content(question, answer, conversation_context)
                            )
                            enhanced_data = future.result()
                    else:
                        enhanced_data = loop.run_until_complete(
                            self._generate_ai_flashcard_content(question, answer, conversation_context)
                        )
                except:
                    enhanced_data = asyncio.run(
                        self._generate_ai_flashcard_content(question, answer, conversation_context)
                    )
            else:
                enhanced_data = self._extract_smart_flashcard_content(question, answer)
            
            # Create flashcard document with enhanced content
            flashcard = {
                "id": flashcard_id,
                "user_id": user_id,
                "front": enhanced_data.get("front", "Study Topic").strip(),
                "back": enhanced_data.get("back", answer).strip(),
                "tags": enhanced_data.get("tags", ["general"]),
                "difficulty": enhanced_data.get("difficulty", 3),
                "mnemonic": enhanced_data.get("mnemonic"),
                "related_concepts": enhanced_data.get("related_concepts", []),
                "source": "ai_conversation",
                "created_date": datetime.utcnow().isoformat(),
                "last_modified": datetime.utcnow().isoformat(),
                "conversation_context": conversation_context or [],
                "ai_enhanced": enhanced_data.get("ai_enhanced", False),
                "deck_name": "AI Conversations",
                "original_question": question,
                "original_answer": answer
            }
            
            # Load existing cards
            cards = self._load_cards()
            if user_id not in cards:
                cards[user_id] = {}
            cards[user_id][flashcard_id] = flashcard
            
            # Save cards
            self._save_cards(cards)
            
            # FIXED: Initialize progress tracking
            self._initialize_flashcard_progress_sync(user_id, flashcard_id)
            
            logger.info(f"✅ Created FIXED flashcard: {flashcard_id}")
            logger.info(f"   Front: {flashcard['front']}")
            logger.info(f"   Back: {flashcard['back'][:50]}...")
            logger.info(f"   AI Enhanced: {flashcard['ai_enhanced']}")
            
            return {
                "success": True,
                "flashcard_id": flashcard_id,
                "flashcard": flashcard,
                "enhanced": enhanced_data.get("ai_enhanced", False),
                "tags": enhanced_data.get("tags", []),
                "difficulty": enhanced_data.get("difficulty", 3)
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to create flashcard: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def _initialize_flashcard_progress_sync(self, user_id: str, flashcard_id: str):
        """FIXED: Initialize progress tracking for a new flashcard - SYNCHRONOUS"""
        try:
            progress_data = self._load_progress()
            
            if user_id not in progress_data:
                progress_data[user_id] = {}
            
            progress_data[user_id][flashcard_id] = {
                "flashcard_id": flashcard_id,
                "review_count": 0,
                "correct_count": 0,
                "incorrect_count": 0,
                "ease_factor": 2.5,
                "interval": 1,  # Days until next review
                "next_review": datetime.utcnow().isoformat(),  # Available immediately
                "last_reviewed": None,
                "streak": 0,
                "created_date": datetime.utcnow().isoformat()
            }
            
            self._save_progress(progress_data)
            logger.info(f"✅ Progress tracking initialized for flashcard {flashcard_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize progress: {e}")

    def get_flashcards_for_review_sync(
        self,
        user_id: str,
        limit: int = 10,
        deck_name: str = None
    ) -> List[Dict[str, Any]]:
        """Get flashcards due for review - SYNCHRONOUS"""
        try:
            cards = self._load_cards()
            progress_data = self._load_progress()
            
            if user_id not in cards:
                return []
            
            user_cards = cards[user_id]
            user_progress = progress_data.get(user_id, {})
            
            current_time = datetime.utcnow().isoformat()
            
            # Find cards due for review
            due_cards = []
            for card_id, card in user_cards.items():
                progress = user_progress.get(card_id, {})
                next_review = progress.get('next_review', current_time)
                
                if next_review <= current_time:
                    card['progress'] = progress
                    if deck_name is None or card.get('deck_name') == deck_name:
                        due_cards.append(card)
            
            # Sort by next_review and limit
            due_cards.sort(key=lambda x: x.get('progress', {}).get('next_review', ''))
            
            logger.info(f"📚 Found {len(due_cards[:limit])} flashcards for review for user {user_id}")
            return due_cards[:limit]
            
        except Exception as e:
            logger.error(f"❌ Failed to get flashcards for review: {e}")
            return []

    def review_flashcard_sync(
        self,
        user_id: str,
        flashcard_id: str,
        correct: bool,
        response_time: int = None
    ) -> Dict[str, Any]:
        """Update flashcard after review - SYNCHRONOUS"""
        try:
            progress_data = self._load_progress()
            
            if user_id not in progress_data or flashcard_id not in progress_data[user_id]:
                return {
                    "success": False,
                    "error": "Flashcard or progress not found"
                }
            
            progress = progress_data[user_id][flashcard_id]
            
            # Update review statistics
            progress['review_count'] += 1
            progress['last_reviewed'] = datetime.utcnow().isoformat()
            
            if correct:
                progress['correct_count'] += 1
                progress['streak'] += 1
            else:
                progress['incorrect_count'] += 1
                progress['streak'] = 0
            
            # Calculate next review using spaced repetition (SM-2 algorithm)
            ease_factor = progress.get('ease_factor', 2.5)
            interval = progress.get('interval', 1)
            
            if correct:
                if progress['review_count'] == 1:
                    interval = 1  # First review after 1 day
                elif progress['review_count'] == 2:
                    interval = 6  # Second review after 6 days
                else:
                    interval = int(interval * ease_factor)
                
                ease_factor = max(1.3, ease_factor + 0.1)
            else:
                interval = 1
                ease_factor = max(1.3, ease_factor - 0.2)
            
            # Calculate next review date
            next_review = datetime.utcnow() + timedelta(days=interval)
            
            # Update progress
            progress['ease_factor'] = round(ease_factor, 2)
            progress['interval'] = interval
            progress['next_review'] = next_review.isoformat()
            
            # Save updated progress
            self._save_progress(progress_data)
            
            logger.info(f"📊 Updated flashcard {flashcard_id}: correct={correct}, next_review={interval} days")
            
            return {
                "success": True,
                "correct": correct,
                "new_interval": interval,
                "ease_factor": ease_factor,
                "next_review": next_review.isoformat(),
                "streak": progress['streak'],
                "total_reviews": progress['review_count']
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to update flashcard review: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def get_user_flashcards_sync(
        self,
        user_id: str,
        limit: int = 50,
        deck_name: str = None
    ) -> List[Dict[str, Any]]:
        """Get all flashcards for a user - SYNCHRONOUS"""
        try:
            cards = self._load_cards()
            
            if user_id not in cards:
                return []
            
            user_cards = list(cards[user_id].values())
            
            # Filter by deck name if specified
            if deck_name:
                user_cards = [card for card in user_cards if card.get('deck_name') == deck_name]
            
            # Sort by created_date (newest first)
            user_cards.sort(key=lambda x: x.get('created_date', ''), reverse=True)
            
            logger.info(f"📚 Retrieved {len(user_cards[:limit])} flashcards for user {user_id}")
            return user_cards[:limit]
            
        except Exception as e:
            logger.error(f"❌ Failed to get user flashcards: {e}")
            return []

    def get_flashcard_stats_sync(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive flashcard statistics for a user - SYNCHRONOUS"""
        try:
            cards = self._load_cards()
            progress_data = self._load_progress()
            
            user_cards = cards.get(user_id, {})
            user_progress = progress_data.get(user_id, {})
            
            total_flashcards = len(user_cards)
            
            # Calculate statistics from progress
            total_reviews = 0
            total_correct = 0
            due_for_review = 0
            current_time = datetime.utcnow().isoformat()
            
            ease_factors = []
            streaks = []
            
            for card_id, progress in user_progress.items():
                total_reviews += progress.get('review_count', 0)
                total_correct += progress.get('correct_count', 0)
                
                # Check if due for review
                next_review = progress.get('next_review', current_time)
                if next_review <= current_time:
                    due_for_review += 1
                
                ease_factors.append(progress.get('ease_factor', 2.5))
                streaks.append(progress.get('streak', 0))
            
            # Calculate accuracy
            accuracy = (total_correct / total_reviews * 100) if total_reviews > 0 else 0
            
            stats = {
                "total_flashcards": total_flashcards,
                "total_reviews": total_reviews,
                "total_correct": total_correct,
                "accuracy": round(accuracy, 1),
                "due_for_review": due_for_review,
                "average_ease_factor": round(sum(ease_factors) / len(ease_factors), 2) if ease_factors else 2.5,
                "longest_streak": max(streaks) if streaks else 0,
                "last_updated": datetime.utcnow().isoformat()
            }
            
            logger.info(f"📊 Stats for user {user_id}: {total_flashcards} cards, {accuracy:.1f}% accuracy")
            return stats
            
        except Exception as e:
            logger.error(f"❌ Failed to get flashcard stats: {e}")
            return {
                "total_flashcards": 0,
                "total_reviews": 0,
                "accuracy": 0,
                "due_for_review": 0,
                "error": str(e)
            }

    def delete_flashcard_sync(self, user_id: str, flashcard_id: str) -> bool:
        """Delete a flashcard and its progress - SYNCHRONOUS"""
        try:
            # Delete from cards
            cards = self._load_cards()
            if user_id in cards and flashcard_id in cards[user_id]:
                del cards[user_id][flashcard_id]
                self._save_cards(cards)
            
            # Delete from progress
            progress_data = self._load_progress()
            if user_id in progress_data and flashcard_id in progress_data[user_id]:
                del progress_data[user_id][flashcard_id]
                self._save_progress(progress_data)
            
            logger.info(f"🗑️ Deleted flashcard {flashcard_id} for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to delete flashcard: {e}")
            return False

    def health_check_sync(self) -> Dict[str, Any]:
        """Health check for flashcard service - SYNCHRONOUS"""
        try:
            # Test file access
            cards = self._load_cards()
            progress_data = self._load_progress()
            
            return {
                "status": "healthy",
                "service": "FlashCard Service",
                "storage": "file-based",
                "cards_file": self.cards_file,
                "progress_file": self.progress_file,
                "connectivity": "successful",
                "cosmos_db": False,  # Using file storage instead
                "ai_enhancement": self.openai_service is not None,
                "features": [
                    "AI-powered flashcard content generation",
                    "Spaced repetition algorithm",
                    "Progress tracking",
                    "Dynamic difficulty assessment",
                    "File-based storage (no async issues)",
                    "Intelligent topic extraction"
                ],
                "total_users": len(cards),
                "total_cards": sum(len(user_cards) for user_cards in cards.values())
            }
            
        except Exception as e:
            logger.error(f"❌ FlashCard service health check failed: {e}")
            return {
                "status": "unhealthy",
                "service": "FlashCard Service",
                "error": str(e),
                "connectivity": "failed",
                "cosmos_db": False
            }

    # Async wrappers for backward compatibility (these just call sync versions)
    async def create_flashcard_from_conversation(self, user_id: str, question: str, answer: str, conversation_context: List[Dict] = None):
        return self.create_flashcard_from_conversation_sync(user_id, question, answer, conversation_context)
    
    async def get_flashcards_for_review(self, user_id: str, limit: int = 10, deck_name: str = None):
        return self.get_flashcards_for_review_sync(user_id, limit, deck_name)
    
    async def review_flashcard(self, user_id: str, flashcard_id: str, correct: bool, response_time: int = None):
        return self.review_flashcard_sync(user_id, flashcard_id, correct, response_time)
    
    async def get_user_flashcards(self, user_id: str, limit: int = 50, deck_name: str = None):
        return self.get_user_flashcards_sync(user_id, limit, deck_name)
    
    async def get_flashcard_stats(self, user_id: str):
        return self.get_flashcard_stats_sync(user_id)
    
    async def delete_flashcard(self, user_id: str, flashcard_id: str):
        return self.delete_flashcard_sync(user_id, flashcard_id)
    
    async def health_check(self):
        return self.health_check_sync()
    
# Add this method to your existing FlashCardService class

async def create_flashcard_from_conversation_with_search(
    self,
    user_id: str,
    question: str,
    answer: str,
    search_results: List[Dict] = None,
    conversation_context: List[Dict] = None
) -> Dict[str, Any]:
    """FIXED: Create flashcard using actual search results content"""
    try:
        # Generate unique flashcard ID
        flashcard_id = str(uuid.uuid4())
        
        # FIXED: Use search results if available, otherwise fall back to AI response
        if search_results and len(search_results) > 0:
            logger.info(f"🔍 Creating flashcard from {len(search_results)} search results")
            enhanced_data = await self._generate_flashcard_from_search_results(
                question, answer, search_results, conversation_context
            )
        else:
            logger.info("🤖 No search results available, using AI response content")
            enhanced_data = await self._generate_ai_flashcard_content(
                question, answer, conversation_context
            )
        
        # Create flashcard document with enhanced content
        flashcard = {
            "id": flashcard_id,
            "user_id": user_id,
            "front": enhanced_data.get("front", "Study Topic").strip(),
            "back": enhanced_data.get("back", answer).strip(),
            "tags": enhanced_data.get("tags", ["general"]),
            "difficulty": enhanced_data.get("difficulty", 3),
            "mnemonic": enhanced_data.get("mnemonic"),
            "related_concepts": enhanced_data.get("related_concepts", []),
            "source": "azure_ai_search" if search_results else "ai_conversation",
            "created_date": datetime.utcnow().isoformat(),
            "last_modified": datetime.utcnow().isoformat(),
            "conversation_context": conversation_context or [],
            "search_enhanced": enhanced_data.get("search_enhanced", False),
            "ai_enhanced": enhanced_data.get("ai_enhanced", False),
            "deck_name": "AI Conversations",
            "original_question": question,
            "original_answer": answer,
            "search_results_used": len(search_results) if search_results else 0
        }
        
        # Load existing cards
        cards = self._load_cards()
        if user_id not in cards:
            cards[user_id] = {}
        cards[user_id][flashcard_id] = flashcard
        
        # Save cards
        self._save_cards(cards)
        
        # Initialize progress tracking
        self._initialize_flashcard_progress_sync(user_id, flashcard_id)
        
        logger.info(f"✅ Created flashcard from search results: {flashcard_id}")
        logger.info(f"   Front: {flashcard['front']}")
        logger.info(f"   Back: {flashcard['back'][:50]}...")
        logger.info(f"   Search Enhanced: {flashcard['search_enhanced']}")
        
        return {
            "success": True,
            "flashcard_id": flashcard_id,
            "flashcard": flashcard,
            "enhanced": enhanced_data.get("ai_enhanced", False),
            "search_enhanced": enhanced_data.get("search_enhanced", False),
            "tags": enhanced_data.get("tags", []),
            "difficulty": enhanced_data.get("difficulty", 3)
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to create flashcard from search: {e}")
        return {
            "success": False,
            "error": str(e)
        }

async def _generate_flashcard_from_search_results(
    self, 
    user_question: str, 
    ai_response: str, 
    search_results: List[Dict],
    conversation_context: List[Dict] = None
) -> Dict[str, Any]:
    """FIXED: Generate flashcard content from actual Azure AI Search results"""
    if not self.openai_service:
        logger.warning("⚠️ OpenAI service not available, using search content extraction")
        return self._extract_flashcard_from_search_content(user_question, search_results)

    try:
        # Combine search results content
        search_content = ""
        source_files = []
        
        for i, result in enumerate(search_results[:3]):  # Use top 3 results
            content = result.get("content", "")
            file_name = result.get("file_name", f"Document {i+1}")
            
            if content:
                search_content += f"\n--- From {file_name} ---\n{content}\n"
                source_files.append(file_name)
        
        if not search_content.strip():
            logger.warning("⚠️ No content found in search results")
            return self._extract_smart_flashcard_content(user_question, ai_response)
        
        # FIXED: Create focused prompt using actual search content
        prompt = f"""Create a study flashcard from this SPECIFIC CONTENT found in the user's documents:

USER QUESTION: {user_question}

ACTUAL CONTENT FROM DOCUMENTS:
{search_content}

Create a focused flashcard that captures the key information from these documents:

FRONT: [Write a clear topic/concept title - NOT a question]
BACK: [Write key points in bullet format using the actual content above]

Rules:
- Use ONLY information from the provided document content
- Front should be a topic title (e.g., "Business Plan 2024 Strategy")
- Back should be bullet points with specific facts from the documents
- Keep it concise and study-friendly
- Focus on the most important information

FRONT: """

        # Generate AI response
        ai_result = await self.openai_service.generate_response(
            user_message=prompt,
            context=[],
            document_chunks=[],
            notion_pages=[],
            max_tokens=300,
            temperature=0.1  # Low temperature for factual content
        )

        # Extract content from AI response
        if isinstance(ai_result, dict):
            ai_text = ai_result.get("assistant_message", str(ai_result))
        else:
            ai_text = str(ai_result)

        logger.info(f"🔍 AI response for search-based flashcard: {ai_text[:100]}...")

        # Parse the AI response
        front, back = self._parse_ai_flashcard_response(ai_text)
        
        if front and back:
            logger.info("✅ Successfully generated flashcard from search results")
            return {
                "front": front.strip(),
                "back": back.strip(),
                "difficulty": self._assess_difficulty(back),
                "tags": self._extract_smart_tags(search_content),
                "mnemonic": None,
                "search_enhanced": True,
                "ai_enhanced": True,
                "source_files": source_files
            }
        else:
            logger.warning("⚠️ AI parsing failed, extracting from search content directly")
            return self._extract_flashcard_from_search_content(user_question, search_results)

    except Exception as e:
        logger.error(f"❌ Search-based flashcard generation failed: {e}")
        return self._extract_flashcard_from_search_content(user_question, search_results)

def _extract_flashcard_from_search_content(
    self, 
    user_question: str, 
    search_results: List[Dict]
) -> Dict[str, Any]:
    """Extract flashcard content directly from search results when AI fails"""
    try:
        if not search_results:
            return self._fallback_extraction(user_question, "No search results available")
        
        # Get the best search result
        best_result = search_results[0]
        content = best_result.get("content", "")
        file_name = best_result.get("file_name", "Document")
        
        if not content:
            return self._fallback_extraction(user_question, "No content in search results")
        
        # Extract topic from file name or content
        front = self._extract_topic_from_content(content, file_name, user_question)
        
        # Extract key points from content
        back = self._extract_key_points_from_content(content)
        
        return {
            "front": front,
            "back": back,
            "difficulty": self._assess_difficulty(back),
            "tags": self._extract_smart_tags(content),
            "mnemonic": None,
            "search_enhanced": True,
            "ai_enhanced": False,
            "source_files": [file_name]
        }
        
    except Exception as e:
        logger.error(f"❌ Direct search content extraction failed: {e}")
        return self._fallback_extraction(user_question, "Search content extraction failed")

def _extract_topic_from_content(self, content: str, file_name: str, user_question: str) -> str:
    """Extract a meaningful topic from search content"""
    try:
        # Try to use file name if it's descriptive
        if file_name and file_name != "Document" and len(file_name) > 5:
            # Clean up file name
            topic = file_name.replace('.pdf', '').replace('.docx', '').replace('_', ' ')
            if len(topic) < 60:
                return topic
        
        # Look for titles or headers in content
        lines = content.split('\n')
        for line in lines[:5]:  # Check first 5 lines
            line = line.strip()
            if line and len(line) < 60 and len(line) > 10:
                # Check if it looks like a title (capitalized, not too long)
                if line[0].isupper() and not line.endswith('.'):
                    return line
        
        # Extract from user question
        if user_question:
            clean_question = re.sub(r'\b(what|how|why|when|where|can|could|would|should|do|does|is|are|about|the)\b', '', user_question.lower())
            clean_question = clean_question.replace('?', '').strip()
            if clean_question:
                return ' '.join(word.capitalize() for word in clean_question.split())[:60]
        
        # Final fallback
        return "Key Information"
        
    except Exception:
        return "Study Topic"

def _extract_key_points_from_content(self, content: str) -> str:
    """Extract key points from search content"""
    try:
        # Look for existing bullet points or numbered lists
        lines = content.split('\n')
        key_points = []
        
        for line in lines:
            line = line.strip()
            # Find existing bullets or numbers
            if re.match(r'^[•\-\*]\s+', line) or re.match(r'^\d+\.\s+', line):
                if len(line) > 10 and len(line) < 200:  # Reasonable length
                    # Normalize to bullet format
                    clean_line = re.sub(r'^[\d\.\-\*•\s]+', '• ', line)
                    key_points.append(clean_line)
                    if len(key_points) >= 5:  # Max 5 points
                        break
        
        if key_points:
            return '\n'.join(key_points)
        
        # If no bullets found, extract sentences
        sentences = re.split(r'[.!?]+', content)
        good_sentences = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if (len(sentence) > 20 and len(sentence) < 150 and 
                not sentence.lower().startswith(('this', 'it', 'they', 'there'))):
                good_sentences.append(f"• {sentence}")
                if len(good_sentences) >= 4:
                    break
        
        if good_sentences:
            return '\n'.join(good_sentences)
        
        # Final fallback: use first part of content
        if len(content) > 50:
            truncated = content[:200].strip()
            if not truncated.endswith('.'):
                truncated += "..."
            return f"• {truncated}"
        
        return f"• {content.strip()}"
        
    except Exception as e:
        logger.error(f"❌ Key points extraction failed: {e}")
        return f"• {content[:100]}..." if content else "• No content available"