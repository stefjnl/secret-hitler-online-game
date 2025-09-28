# Secret Hitler Online Game

A browser-based implementation of Secret Hitler where 1-2 human players join 6-7 AI players in a complete 8-player game.

## Project Setup

### Prerequisites

*   Python 3.9+
*   Git

### Installation

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/stefjnl/secret-hitler-online-game.git
    cd secret-hitler-online-game
    ```

2.  **Create and activate a virtual environment:**

    ```bash
    python -m venv venv
    # On Windows
    .\venv\Scripts\activate
    # On macOS/Linux
    source venv/bin/activate
    ```

3.  **Install the dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

## Running the Application

To run the application in development mode with live reloading, use the following command:

```bash
uvicorn main:app --reload
```

The application will be available at `http://localhost:8000`.

## VS Code Configuration

This repository includes a `.vscode/settings.json` file to ensure a consistent development environment. It is recommended to use the official [Python extension for Visual Studio Code](https://marketplace.visualstudio.com/items?itemName=ms-python.python).

The provided settings will:
*   Automatically select the project's virtual environment as the interpreter.
*   Enable linting with Pylint to help enforce coding standards.