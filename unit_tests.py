import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import pymongo
import json
from typing import Dict

# Import your classes
from grading_system import GradingSystem, GradingResult, MongoDBCache

class TestMongoDBCache(unittest.TestCase):
    def setUp(self):
        """Set up test cases"""
        self.cache = MongoDBCache(
            connection_string="mongodb://localhost:27017/",
            database_name="test_qa_grading_cache",
            cache_expiry_hours=24
        )
        
        # Clear test database before each test
        self.cache.cache_collection.delete_many({})

    def test_store_and_retrieve_result(self):
        """Test storing and retrieving results from cache"""
        session_id = "session_123"
        test_results = {
            "total_points": 85,
            "max_points": 100,
            "feedback": "Good job!"
        }
        
        # Store results
        self.cache.store_result(session_id, test_results)
        
        # Retrieve results
        cached_result = self.cache.get_cached_result(session_id)
        
        self.assertEqual(cached_result, test_results)

    def test_cache_miss(self):
        """Test behavior when cache miss occurs"""
        result = self.cache.get_cached_result("nonexistent_session")
        self.assertIsNone(result)

    def tearDown(self):
        """Clean up after tests"""
        self.cache.cache_collection.delete_many({})
        self.cache.client.close()

class TestGradingSystem(unittest.TestCase):
    def setUp(self):
        """Set up test cases"""
        self.grading_system = GradingSystem(use_cache=False)
        
    @patch('google.generativeai.GenerativeModel')
    def test_grade_answer(self, mock_model):
        """Test grading a single answer"""
        # Mock the model response
        mock_response = MagicMock()
        mock_response.text = "GRADE: 8\nFEEDBACK: Good understanding shown"
        mock_model.return_value.generate_content.return_value = mock_response

        result = self.grading_system.grade_answer(
            question="What is Python?",
            student_answer="Python is a programming language.",
            max_points=10
        )

        self.assertIsInstance(result, GradingResult)
        self.assertEqual(result.points, 8)
        self.assertEqual(result.max_points, 10)
        self.assertEqual(result.feedback, "Good understanding shown")

    def test_validate_payload_valid(self):
        """Test payload validation with valid data"""
        valid_payload = {
            "timestamp": datetime.now().isoformat(),
            "session_id": "session_123",
            "answers": [{
                "question_id": "q1",
                "question": "What is Python?",
                "student_answer": "A programming language",
                "max_points": 10
            }]
        }
        
        result = self.grading_system.validate_payload(valid_payload)
        self.assertTrue(result)

    def test_validate_payload_invalid(self):
        """Test payload validation with invalid data"""
        invalid_payloads = [
            # Missing required keys
            {
                "session_id": "session_123",
                "answers": []
            },
            # Invalid session_id format
            {
                "timestamp": datetime.now().isoformat(),
                "session_id": "invalid",
                "answers": []
            },
            # Invalid answers format
            {
                "timestamp": datetime.now().isoformat(),
                "session_id": "session_123",
                "answers": "not_a_list"
            },
            # Missing required answer keys
            {
                "timestamp": datetime.now().isoformat(),
                "session_id": "session_123",
                "answers": [{
                    "question": "What is Python?"
                }]
            }
        ]

        for payload in invalid_payloads:
            result = self.grading_system.validate_payload(payload)
            self.assertIsInstance(result, str)
            self.assertTrue(result.startswith("Payload validation error"))

    def test_generate_overall_feedback(self):
        """Test overall feedback generation"""
        test_cases = [
            {"percentage": 100, "expected": "Perfect score! Outstanding performance!"},
            {"percentage": 85, "expected": "Excellent work! Just a few minor improvements needed."},
            {"percentage": 65, "expected": "Good effort, but there's room for improvement."},
            {"percentage": 45, "expected": "You're on the right track, but need to review the material more thoroughly."},
            {"percentage": 30, "expected": "This topic needs significant review. Consider seeking additional help."}
        ]

        for case in test_cases:
            result = self.grading_system.generate_overall_feedback({
                "percentage": case["percentage"]
            })
            self.assertEqual(result, case["expected"])

    @patch('google.generativeai.GenerativeModel')
    def test_process_qa_data(self, mock_model):
        """Test processing complete Q&A data"""
        # Mock the model response
        mock_response = MagicMock()
        mock_response.text = "GRADE: 8\nFEEDBACK: Good understanding shown"
        mock_model.return_value.generate_content.return_value = mock_response

        test_data = {
            "timestamp": datetime.now().isoformat(),
            "session_id": "session_123",
            "answers": [{
                "question_id": "q1",
                "question": "What is Python?",
                "student_answer": "A programming language",
                "max_points": 10
            }]
        }

        result = self.grading_system.process_qa_data(test_data)

        self.assertEqual(result["session_id"], "session_123")
        self.assertIn("total_points", result)
        self.assertIn("max_points", result)
        self.assertIn("percentage", result)
        self.assertIn("graded_answers", result)
        self.assertIn("overall_feedback", result)

if __name__ == '__main__':
    unittest.main()