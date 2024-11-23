# AI-Powered Q&A Grading System

## Project Overview
This project is an automated Q&A grading system using WebSocket communication and AI-powered grading. This is a submission for the assignment from Systemic Altruism, submitted by Rishit Chugh.

Note that a sample results json is already included inside the results directory for you to view.

Decision Making and Optimisation Strategies are present at the end of this readme file

## System Requirements
- Python 3.8+
- pip (Python package manager)

## Dependencies Installation
```bash
pip install websockets google-generativeai asyncio pymongo
```

## Project Structure
- `mock_websocket_server.py`: WebSocket server that generates Q&A payloads
- `grading_system`: module that contains grading logic
- `grading_system.py`: Client to recieve messages from the server and interact with the grading system to output results

## Running the Project
Make sure to add your Gemini API Key in grading_system/main.py (line 36)

### Step 0: Install MongoDB
```bash
# Download MongoDB Community Server from:
https://www.mongodb.com/try/download/community

# After installation, create a data directory:
md C:\data\db

# Start MongoDB server:
"C:\Program Files\MongoDB\Server\{version}\bin\mongod.exe"

# Install MongoDB for MACOS
brew tap mongodb/brew
brew install mongodb-community

# Start MongoDB service
brew services start mongodb-community

```
### Step 1: Start WebSocket Server
Open a terminal and run:
```bash
python3 mock_websocket_server.py
```
Server will start on `ws://localhost:8765`

### Step 2: Run Grading Client
Open another terminal and run:
```bash
python grading_system.py
```

### Optional: Run Unit tests to check everything is working as intended
```bash
python -m unittest unit_tests.py
```


### Interaction Flow
1. Server automatically sends first Q&A payload
2. Grading results are displayed
3. Prompted to:
   - Grade another set (type 'yes')
   - Request a incorrect payload to check edge-cases (type 'wrong')
   - Exit (type 'no')

## Troubleshooting
- Ensure all dependencies are installed
- Check that no other services are using port 8765
- Verify Python, mongoDB and pip are correctly installed

## Decision Making and Optimisation Steps taken

- The grading solution is made into a class based approach and implemented like a module/library. It is present inside the grading_system directory inside main.py. the init file allows us to use the class outside the directory. The files directory contains a text file containing the Engineered prompt used to get our results. This is to avoid clutter inside the code and aid reproducability

- A mock websocket server was created that randomly sends a json containing questions and their respective answers given by a student. The first message is sent automatically when a connection is established and a recieve command is sent. You can request more questions or request faulty json to check error handling. The main code will prompt you inside the terminal to ask you what to do. Inside the code it sends messages to server to recieve more questions

- The implementation and orchestration between the server and the grading system is handled by grading_system.py in the root directory. This is done to show how easily the grading library can be used outside it and how to connect to a websocket

- Caching is implemented through mongoDB which is a design choice and inudstry standard for storing conversations with LLMs. It is fast and efficient. retrieving is based on the session ID which is randomised and mocked for this implementation however you can confirm its working by running the unit tests.

- Concurrent users is handled through creating asynchronous functions that will act independently for each connected user. This should be good enough for medium load.

- Unit Tests are inside the unit_tests.py inside the root directory

## Optimisation Strategies:
- MongoDB Caching for retrieval (Saves tokens incase a similar assignment was already graded before)
- Uses logging for debugging and monitoring
- Modular design and and independent components
- Async functions
- Use of data classes
- Type casting and default values