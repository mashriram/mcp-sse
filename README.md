# MCP Streamlit Chat Client

This application provides a Streamlit-based web interface for chatting with a large language model (LLM) that can use tools from one or more MCP (Model Context Protocol) servers.

## Features

- **Web-based Chat Interface**: A user-friendly chat interface built with Streamlit.
- **Connect to MCP Servers**: Connect to multiple MCP servers to make their tools available to the LLM.
- **Groq Integration**: Uses the Groq API for fast LLM inference.
- **Dynamic Tool Usage**: The LLM can decide which tools to use based on the user's query.

## Setup and Usage

### 1. Prerequisites

- Python 3.8+
- `uv` (or `pip`) for package installation.

### 2. Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd <repository-directory>
    ```

2.  **Install the dependencies:**
    ```bash
    uv pip install -r requirements.txt
    ```

### 3. Configure your API Key

The application requires a Groq API key. You can provide it in one of two ways:

-   **Environment Variable**: Create a `.env` file in the root of the project and add the following line:
    ```
    GROQ_API_KEY="your-groq-api-key"
    ```
-   **In the UI**: Paste your API key directly into the "Groq API Key" field in the application's sidebar.

### 4. Running the MCP Servers

This client is designed to connect to MCP servers. An example `weather.py` server is provided. You can run it as follows:

```bash
uv run weather.py
```

By default, the weather server runs on `http://localhost:8080`. You can run multiple servers on different ports and add them to the `AVAILABLE_SERVERS` dictionary in `app.py`.

### 5. Running the Streamlit App

Once the dependencies are installed and the MCP servers are running, you can start the Streamlit application:

```bash
streamlit run app.py
```

The application will open in your web browser. You can then enter your Groq API key, select the MCP servers you want to use, and start chatting with the LLM.
