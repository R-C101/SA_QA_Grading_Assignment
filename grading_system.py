import asyncio
import websockets
from grading_system import GradingSystem
import logging
import json

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def grade_qa_from_server(uri: str = "ws://localhost:8765"):
    """
    Connect to WebSocket server, receive Q&A data, and process it with caching
    """
    grading_system = GradingSystem(use_cache=True)  # Enable caching
    
    try:
        async with websockets.connect(uri) as websocket:
            logger.info("Connected to Q&A server")
            
            while True:
                try:
                    message = await websocket.recv()
                    qa_data = json.loads(message)
                    logger.info("Received Q&A data from server")
                    
                    # Process and grade the answers (now with caching)
                    results = grading_system.process_qa_data(qa_data)
                    
                    print("\nGrading Results:")
                    print(json.dumps(results, indent=2))
                    
                    with open("results/results.json", "w") as f:
                        json.dump(results, f)
                    
                    user_input = input("\nWould you like to grade another set? (type 'wrong' to check for edge case) (yes/no): ")
                    if user_input.lower() == 'no':
                        break
                    
                    if user_input.lower() == 'wrong':
                        await websocket.send("wrong")
                    else:
                        await websocket.send("next")
                    
                except json.JSONDecodeError:
                    logger.error("Invalid JSON data received from server")
                    break
                except Exception as e:
                    logger.error(f"Error processing Q&A data: {str(e)}")
                    break
                    
    except websockets.exceptions.ConnectionClosed:
        logger.error("Connection to server closed")
    except Exception as e:
        logger.error(f"Error connecting to server: {str(e)}")



if __name__ == "__main__":
    print("Starting grading client...")
    print("Connecting to Q&A server...")
    
    asyncio.run(grade_qa_from_server())