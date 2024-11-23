import asyncio
import websockets
import json
import logging
from datetime import datetime
import random

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class QAWebSocketServer:
    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.active_connections = set()
        
        # Sample Q&A database
        self.qa_database = [
    {
        "question_id": "q1",
        "question": "What is a neural network?",
        "student_answer": "A neural network is a computational model inspired by the way biological neural networks in the human brain process information. It consists of layers of interconnected nodes called neurons, which can learn patterns and relationships in data through a process of training and optimization.",
        "max_points": 5
    },
    {
        "question_id": "q2",
        "question": "What is supervised learning?",
        "student_answer": "Supervised learning is a machine learning technique where a model learns from labeled data. The model is trained using input-output pairs, and the goal is to minimize errors by predicting outputs accurately during the training process.",
        "max_points": 4
    },
    {
        "question_id": "q3",
        "question": "What is overfitting in machine learning?",
        "student_answer": "Overfitting happens when the model is too large for the dataset and can be avoided by increasing the number of layers in a neural network.",
        "max_points": 4
    }
]
        self.wrong_db = []

    async def send_qa_data(self, websocket, message_req = None):
        """Sends Q&A data to the connected client"""
        try:
            # Randomly select 2-3 questions from the database
            num_questions = random.randint(2, 3)
            selected_questions = random.sample(self.qa_database, num_questions)
            
            message = {
                "timestamp": datetime.utcnow().isoformat(),
                "session_id": f"session_{random.randint(1000, 9999)}",
                "answers": selected_questions
            }
            if message_req == "wrong":
                await websocket.send(json.dumps(self.wrong_db))
            else:
                await websocket.send(json.dumps(message))
            logger.info(f"Sent Q&A data to client")
            
        except Exception as e:
            logger.error(f"Error sending Q&A data: {str(e)}")

    async def handle_connection(self, websocket):
        """Handle individual WebSocket connections"""
        client_id = id(websocket)
        self.active_connections.add(websocket)
        logger.info(f"New connection established. Client ID: {client_id}")
        
        try:
            # Send Q&A data immediately upon connection
            await self.send_qa_data(websocket)
            
            # Keep connection open and handle any incoming messages
            async for message in websocket:
                # If client sends "next", send new Q&A data
                if message.lower() == "next":
                    await self.send_qa_data(websocket)
                elif message.lower() == "wrong":
                    await self.send_qa_data(websocket,message)
                    
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client {client_id} connection closed")
        finally:
            self.active_connections.remove(websocket)

    async def start(self):
        """Start the WebSocket server"""
        async with websockets.serve(self.handle_connection, self.host, self.port):
            logger.info(f"Q&A Server started on ws://{self.host}:{self.port}")
            await asyncio.Future()  # run forever

# Run the server
if __name__ == "__main__":
    server = QAWebSocketServer()
    asyncio.run(server.start())