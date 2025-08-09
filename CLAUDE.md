# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Streamlit demo application showcasing basic web app features including data visualization, interactive components, and a chat interface. The application is containerized and designed for deployment on Azure Web Apps with OIDC authentication.

## Development Commands

### Running the Application
```bash
streamlit run src/main.py
```
The app will be available at http://localhost:8501

### Installing Dependencies
```bash
pip install -r requirements.txt
```

### Code Quality
```bash
# Linting with flake8 (configured in setup.cfg)
flake8 src/

# Format code with Black (VS Code configured to auto-format)
black src/
```

### Testing
```bash
# Run tests if they exist (configured for pytest in setup.cfg)
pytest
```

## Architecture

### Application Structure
The application uses Streamlit's multi-page navigation system:

- **src/main.py**: Entry point with navigation setup using `st.Page` and `st.navigation`
- **src/demo.py**: Interactive demo page with data visualization (charts, dataframes) and UI controls (sliders, buttons)
- **src/chat.py**: Chat interface demo with session state management for conversation history

### Key Streamlit Patterns
- **Page Navigation**: Uses `st.Page` and `st.navigation` for multi-page apps
- **Session State**: `st.session_state` for maintaining chat history and user interactions
- **Data Visualization**: `st.line_chart`, `st.dataframe` for displaying data
- **User Inputs**: `st.slider`, `st.button`, `st.chat_input` for interactions
- **Chat UI**: `st.chat_message` for conversation display

### Infrastructure
- **Container**: Dev Container with Python 3.11, Azure CLI, and GitHub CLI pre-installed
- **Deployment**: Azure Web Apps with OIDC authentication via Bicep templates
- **Security**: Key Vault integration for secrets management
- **CI/CD**: GitHub Actions workflow support with OIDC federated credentials

### Azure Deployment
The infrastructure/ directory contains:
- **main.bicep**: Azure resource definitions (Web App, Key Vault, Container Registry, Managed Identity)
- **deploy.sh**: Two-stage deployment script handling resource creation and permissions
- **cleanup.sh**: Resource cleanup utilities

## Development Environment

### Dev Container Features
- Python 3.11 base image
- Pre-installed tools: git, gh (GitHub CLI), Azure CLI
- VS Code extensions: Python, Black formatter, Flake8, Bicep
- Port 8501 forwarded for Streamlit
- Mounts for .claude, .azure credentials

### Environment Variables
Required in .env file for deployment:
- RESOURCE_GROUP: Azure resource group name
- APP_NAME: Application name prefix for Azure resources
- GITHUB_TOKEN: GitHub PAT for container registry access
- GITHUB_REPO_OWNER: GitHub username/organization
- GITHUB_REPO_NAME: Repository name
- LOCATION: Azure region (e.g., japaneast)

## Important Notes
- The application uses Japanese text in comments and UI elements
- Streamlit runs on port 8501 by default
- Data in demo.py is randomly generated on each app restart
- Chat responses in chat.py are rule-based (not AI-powered)