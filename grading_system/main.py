import asyncio
import websockets
import json
import logging
from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime
import google.generativeai as genai
import os
import pymongo

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class GradingResult:
    points: int
    max_points: int
    feedback: str

class MongoDBCache:
    def __init__(self, 
                 connection_string: str = "mongodb://localhost:27017/", 
                 database_name: str = "qa_grading_cache",
                 cache_expiry_hours: int = 24):
        """
        Initialize MongoDB cache connection
        """
        try:
            self.client = pymongo.MongoClient(connection_string)
            self.db = self.client[database_name]
            self.cache_collection = self.db["grading_results"]
            
            # Create index for efficient querying and automatic expiry
            self.cache_collection.create_index(
                "timestamp", 
                expireAfterSeconds=cache_expiry_hours * 3600
            )
            logger.info("Successfully connected to MongoDB")
        except Exception as e:
            logger.error(f"MongoDB connection error: {e}")
            raise

    def store_result(self, session_id: str, results: Dict):
        """
        Store grading results in MongoDB cache
        """
        cache_entry = {
            "session_id": session_id,
            "results": results,
            "timestamp": datetime.utcnow()
        }
        
        try:
            self.cache_collection.update_one(
                {"session_id": session_id}, 
                {"$set": cache_entry}, 
                upsert=True
            )
            logger.info(f"Cached results for session {session_id}")
        except Exception as e:
            logger.error(f"Error caching results: {e}")

    def get_cached_result(self, session_id: str) -> Optional[Dict]:
        """
        Retrieve cached grading results
        """
        try:
            cached_result = self.cache_collection.find_one(
                {"session_id": session_id}
            )
            
            if cached_result:
                logger.info(f"Cache hit for session {session_id}")
                return cached_result["results"]
            
            logger.info(f"Cache miss for session {session_id}")
            return None
        except Exception as e:
            logger.error(f"Error retrieving cached result: {e}")
            return None

class GradingSystem:
    def __init__(self, use_cache: bool = True):
        """Initialize GradingSystem with optional caching"""
        self.cache = MongoDBCache() if use_cache else None

    def load_prompt_template(self, file_path='grading_system/files/prompt.txt'):
        """Load the prompt template from a file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except FileNotFoundError:
            raise Exception(f"Prompt template file not found at: {file_path}")

    def call_model(self, question: str, answer: str, max_points: int) -> str:
        genai.configure(api_key='your api key here')
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = self.load_prompt_template()
        query_format = f"""
            QUESTION: {question}
            ANSWER: {answer}
            MAX_POINTS: {max_points}
            """
        prompt = prompt + query_format
        response = model.generate_content(prompt)
        return response.text

    def grade_answer(self, question: str, student_answer: str, max_points: int) -> GradingResult:
        """Grade a single answer and provide feedback"""
        response = self.call_model(question, student_answer, max_points)
        lines = response.strip().split('\n')
        points = float(lines[0].replace('GRADE: ', ''))
        feedback = lines[1].replace('FEEDBACK: ', '')

        return GradingResult(
            points=points,
            max_points=max_points,
            feedback=feedback
        )

    def process_qa_data(self, data: Dict) -> Dict:
        """Process the Q&A data with caching"""
        # Check cache first if enabled
        if self.cache:
            cached_result = self.cache.get_cached_result(data["session_id"])
            if cached_result:
                logger.info(f"Returning cached result for session {data['session_id']}")
                return cached_result

        # Validate payload
        result = self.validate_payload(data)
        if result is not True:
            return {
                "status": "error",
                "message": result
            }

        # Process answers
        results = {
            "session_id": data["session_id"],
            "timestamp": datetime.utcnow().isoformat(),
            "total_points": 0,
            "max_points": 0,
            "percentage": 0,
            "graded_answers": []
        }

        for answer in data["answers"]:
            graded = self.grade_answer(
                answer['question'],
                answer["student_answer"],
                answer["max_points"]
            )

            results["total_points"] += graded.points
            results["max_points"] += graded.max_points

            results["graded_answers"].append({
                "question_id": answer.get("question_id", "unknown"),
                "question": answer["question"],
                "student_answer": answer["student_answer"],
                "points": graded.points,
                "max_points": graded.max_points,
                "feedback": graded.feedback,
            })

        if results["max_points"] > 0:
            results["percentage"] = round(
                (results["total_points"] / results["max_points"]) * 100, 2)

        results["overall_feedback"] = self.generate_overall_feedback(results)

        # Store in cache if enabled
        if self.cache:
            self.cache.store_result(data["session_id"], results)
            logger.info(f"Stored results in cache for session {data['session_id']}")

        return results

    def generate_overall_feedback(self, results: Dict) -> str:
        """Generate overall feedback based on performance"""
        percentage = results["percentage"]
        if percentage == 100:
            return "Perfect score! Outstanding performance!"
        elif percentage >= 80:
            return "Excellent work! Just a few minor improvements needed."
        elif percentage >= 60:
            return "Good effort, but there's room for improvement."
        elif percentage >= 40:
            return "You're on the right track, but need to review the material more thoroughly."
        else:
            return "This topic needs significant review. Consider seeking additional help."

    def validate_payload(self, payload):
        """Validate the input payload"""
        try:
            if not isinstance(payload, dict):
                raise ValueError("Payload must be a dictionary.")

            required_keys = {"timestamp", "session_id", "answers"}
            if not required_keys.issubset(payload.keys()):
                raise KeyError(
                    f"Payload is missing required keys: {required_keys - payload.keys()}")

            try:
                datetime.fromisoformat(payload["timestamp"])
            except ValueError:
                raise ValueError("Invalid timestamp format. Expected ISO 8601 format.")

            if not isinstance(payload["session_id"], str) or not payload["session_id"].startswith("session_"):
                raise ValueError(
                    "Invalid session_id format. Must be a string starting with 'session_'.")

            if not isinstance(payload["answers"], list):
                raise TypeError("Answers must be a list.")
            if not payload["answers"]:
                raise ValueError("Answers list cannot be empty.")

            required_answer_keys = {
                "question_id", "question", "student_answer", "max_points"}
            for answer in payload["answers"]:
                if not isinstance(answer, dict):
                    raise TypeError("Each answer must be a dictionary.")
                if not required_answer_keys.issubset(answer.keys()):
                    missing_keys = required_answer_keys - answer.keys()
                    raise KeyError(
                        f"An answer is missing required keys: {missing_keys}")
                if not isinstance(answer["max_points"], (int, float)) or answer["max_points"] <= 0:
                    raise ValueError("max_points must be a positive number.")

            return True

        except (KeyError, TypeError, ValueError) as e:
            return f"Payload validation error: {e}"
        
        
            