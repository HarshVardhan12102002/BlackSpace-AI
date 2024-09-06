# 🌌 blackspace.ai

# AI-Powered Sales Assistant

blackspace.ai is designed to streamline the process of gathering customer data and generating tailored sales proposals. The tool utilizes large language models (LLMs) and speech recognition technologies to interact with users, analyze inputs, and automatically generate detailed sales documents.

## 🚀Key Features

- **🎤Voice Activation**: Supports voice along with text inputs to facilitate usage during live conversations, meetings, and phone calls.
- **💬Interactive Engagement**: Guides users through relevant questions to gather all critical details required for a tailored proposal.
- **📄Document Analysis**: Ability to analyze documents (PDF) provided by the customer to extract required information for drafting the sales proposal.
- **🔍Information Gap Analysis**: Identifies and prompts for any missing details necessary for completing the sales proposal.

## 🛠Technical Requirements

- **🧠LLM Integration**: Integration with any large language model for natural language understanding and generation.
- **🗣Speech Recognition**: Speech recognition to convert speech to text for processing user inputs.

## 🌟Getting Started

### 📦Installation

Clone the repository:

   ```bash
   git clone https://github.com/srikanta30/blackspace-ai.git
   ```

Make sure you have a **python >=3.8,<3.12**:

Create a virtual environment at a location on your computer. We use the generic "env" name for our virtual environment in the setup. You can rename this, but make sure to then use this name later when working with the environment (also rename the VENV variable in the Makefile accordingly to be able to use make commands successfully after cloning our repository):

### For Windows:

- Open Command Prompt or PowerShell.
- Navigate to your project directory: `cd path\to\your\project`
- Create a virtual environment: `python -m venv env`
- Activate the virtual environment: `.\env\Scripts\activate`

### For Mac:

- Open Terminal.
- Navigate to your project directory: `cd path/to/your/project`
- Create a virtual environment: `python3 -m venv env`
- Activate the virtual environment: `source env/bin/activate`

To deactivate a virtual environment after you have stopped using it simply run: `deactivate`

### Frontend/UI:
- cd `client` folder.
- `npm install`.
- `npm run dev`


### Using Docker
For those who prefer containerization, Docker offers an isolated and consistent environment. Ensure Docker is installed on your system by following the [official Docker installation guide](https://docs.docker.com/get-docker/).

To run blackspace.ai with Docker, execute the following steps:

1. **Start the Application with Docker Compose:**

   Use the command below to start blackspace.ai in detached mode:
   ```
   docker-compose up -d
   ```
   If you've made changes and want them to reflect, append `--build` to the command above.

2. **Stopping the Application:**

   To stop and remove all running containers related to blackspace.ai, execute:
   ```
   docker-compose down
   ```

**Troubleshooting:**

- **Clean Up Docker Resources:** If you encounter errors, you can clean up Docker by removing all unused containers, networks, images, and volumes with caution:
  ```
  docker system prune --volumes
  ```
- **Rebuild Without Cache:** To rebuild and start the services afresh without using cache, run:
  ```
  docker-compose up -d --build --no-cache
  ```

After successful setup, access blackspace.ai at [localhost:3000/chat](http://localhost:3000/chat) in your browser.

### 2. Direct User Interface Launch
If Docker is not part of your workflow, you can directly launch the blackspace.ai user interface. Please refer to the `README.md` file in the frontend directory for instructions on setting up the UI locally.

### 3. Using the Terminal
For terminal enthusiasts or automation scripts, run blackspace.ai with the following command:
`python run.py --verbose True --config examples/example_agent_setup.json`

### 4. Running Only the Backend
For those who wish to integrate blackspace.ai's backend with their own user interface or application, running only the backend is a straightforward process. This allows you to leverage the powerful features of blackspace.ai while maintaining full control over the user experience.

To run only the backend of blackspace.ai, follow these steps:
1. **Start the Backend Service:**

   Use the following command to start the backend service. This will initiate the server on port 8000 by default, making the API accessible:
   ```
   docker-compose up -d backend
   ```

   If you need to rebuild the backend image, perhaps after making changes, you can add `--build` to the command above.

2. **Accessing the Backend:**

   With the backend running, you can access the API endpoints at `http://localhost:8000`. Refer to the API documentation for details on available endpoints and their usage.

3. **Stopping the Backend:**

   To stop the backend service, execute:
   ```
   docker-compose stop backend
   ```

   If you wish to remove the backend container entirely, use:
   ```
   docker-compose down
   ```
