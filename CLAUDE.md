# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

X Scheduler Pro - A Streamlit-based X (Twitter) post management system with OAuth 2.0 authentication, immediate/scheduled posting, rate limit management, and Firebase integration. The application has been restructured to support multiple applications under the `application/` directory.

## Development Commands

### Running the Application
```bash
# Run the Streamlit frontend application
streamlit run application/frontend/main.py

# The app will be available at http://localhost:8501
```

### Installing Dependencies
```bash
# Install frontend dependencies
pip install -r application/frontend/requirements.txt
```

### Code Quality
```bash
# Linting with flake8 (configured in setup.cfg)
flake8 application/frontend/

# Format code with Black
black application/frontend/

# Run tests if they exist
pytest
```

### Docker Operations
```bash
# Build Docker image locally
cd application/frontend
docker build -t x-scheduler-pro .

# Run container locally
docker run -p 8501:8501 x-scheduler-pro
```

### Azure Deployment
```bash
# Deploy infrastructure and application
cd infrastructure
./deploy.sh

# Clean up Azure resources
./cleanup.sh
```

### Azure Functions Development
```bash
# Install Azure Functions Core Tools
# Ubuntu/WSL
sudo apt-get update
sudo apt-get install azure-functions-core-tools-4

# Initialize Functions project
cd application/functions
func init --python

# Create new timer trigger function
func new --name auto_poster --template "Timer trigger"

# Run Functions locally
func start

# Deploy to Azure
func azure functionapp publish ${APP_NAME}-functions
```

## Architecture

### Project Structure
The codebase follows a multi-application architecture:
- **application/frontend/**: Streamlit web application
- **application/functions/**: Azure Functions for automated posting (planned)
  - Timer-triggered functions for scheduled posts
  - Firestore integration for post management
- **infrastructure/**: Azure deployment scripts and Bicep templates
- **.github/workflows/**: GitHub Actions CI/CD pipelines

### Frontend Application Architecture

#### Authentication Flow
- **OAuth 2.0 + PKCE**: Secure authentication using X API v2
- **Token Management**: Auto-refresh with encrypted storage in session state
- **Session Handling**: 30-minute timeout with state persistence via StateStore

#### Core Components

1. **X API Integration** (`api/x_api_client.py`)
   - Tweet posting via X API v2
   - Rate limit tracking (17 posts/24h, 500 posts/month)
   - Error handling with custom exception hierarchy

2. **Authentication** (`auth/oauth_client.py`)
   - OAuth 2.0 Authorization Code Flow with PKCE
   - Token exchange and refresh
   - User info retrieval

3. **Data Persistence** (`db/firebase_client.py`)
   - Singleton Firebase client
   - Encrypted token storage
   - Post history and statistics tracking
   - Support for both service account file and Base64-encoded credentials
   - Collections: 
     - `posts`: content, postDate (YYYY/MM/DD), timeSlot (0-3), isPosted
     - `users`, `rate_limits` (planned for Functions integration)

4. **UI Components** (`components/`)
   - `simple_file_viewer.py`: Markdown file browser with 2-pane preview
   - `post_history.py`: Post history display with search and filtering

5. **Configuration** (`utils/config.py`)
   - Centralized configuration management
   - Environment variable and Streamlit Secrets support
   - OAuth endpoints and rate limits

### Azure Functions Architecture (Planned)

#### Automated Posting System
- **Timer Trigger**: Executes at 09:00, 12:00, 15:00, 21:00 to check for scheduled posts
- **Time Slot Management**: Uses predefined slots (0-3) for posting times
- **Firestore Integration**: Queries posts by timeSlot and postDate fields
- **Token Management**: Retrieves and decrypts user access tokens (future implementation)
- **X API Integration**: Posts tweets and updates isPosted status in Firestore
- **Error Handling**: Updates errorMessage field and logs failures

### Infrastructure & Deployment

#### Azure Resources (Bicep)
- **App Service**: Linux container hosting with sidecar support
- **Functions App**: Serverless execution for automated posting (Timer Trigger)
- **Storage Account**: Functions runtime storage
- **Key Vault**: Secure storage for GitHub token, X API credentials, and encryption keys
- **Container Registry**: GitHub Container Registry (ghcr.io) integration
- **Managed Identity**: OIDC authentication for GitHub Actions

#### GitHub Actions Workflow
- **Build & Push**: Docker image to ghcr.io
- **Deploy**: Azure Web App deployment with OIDC
- **Context-aware Build**: Uses `context: ./application/frontend` with relative Dockerfile path

### Security Considerations

1. **Token Security**
   - Tokens encrypted with Fernet symmetric encryption
   - Session-based storage only, no persistent local storage
   - Automatic cleanup on logout

2. **CSRF Protection**
   - State parameter validation in OAuth flow
   - PKCE challenge verification

3. **Rate Limiting**
   - Client-side tracking before API calls
   - Firestore persistence of usage data
   - Rolling window for daily limits

## Important Configuration Notes

### Environment Variables
Required in `.env` file:
- `X_CLIENT_ID`, `X_CLIENT_SECRET`: X API OAuth credentials
- `X_REDIRECT_URI`: OAuth callback URL (default: http://localhost:8501)
- `FIREBASE_PROJECT_ID`: Firebase project identifier
- `FIREBASE_SERVICE_ACCOUNT_BASE64`: Base64-encoded service account JSON
- `ENCRYPTION_KEY`: Fernet encryption key for token storage
- `GITHUB_TOKEN`: For container registry access
- Azure deployment variables: `RESOURCE_GROUP`, `APP_NAME`, `LOCATION`

For Azure Functions (`local.settings.json`):
- `FUNCTIONS_WORKER_RUNTIME`: python
- `AzureWebJobsStorage`: Storage connection string
- `WEBSITE_TIME_ZONE`: Asia/Tokyo (for scheduled posts)

### Docker Context
The Dockerfile is located at `application/frontend/Dockerfile` and uses:
- Build context: `application/frontend/`
- All paths in Dockerfile are relative to this context
- Copies entire frontend directory with `COPY . .`

### Import Structure
All Python imports within the frontend app use relative imports:
- `from auth.oauth_client import ...` (not `from src.auth...`)
- Module resolution works from `application/frontend/` as the base

## Common Development Tasks

### Adding a New Application
1. Create new directory under `application/` (e.g., `application/backend/`)
2. Add application-specific Dockerfile in the new directory
3. Update GitHub Actions workflow if needed for multi-app deployment

### Setting up Azure Functions
1. Initialize Functions project: `func init --python`
2. Create timer trigger: `func new --name auto_poster --template "Timer trigger"`
3. Configure `local.settings.json` with Firebase credentials
4. Update `host.json` and `function.json` for timer schedule
5. Deploy using `func azure functionapp publish`

### Debugging Authentication Issues
1. Check redirect URI matches X API app settings
2. Verify environment variables are loaded
3. Check StateStore for PKCE verifier persistence
4. Review OAuth state parameter validation

### Handling Rate Limits
- Monitor via the rate limit display in the UI
- Check Firestore for historical usage data
- Daily limits reset on 24-hour rolling window
- Monthly limits reset on calendar month

## Testing & Validation

### Local Testing
```bash
# Test Streamlit app startup
streamlit run application/frontend/main.py

# Verify OAuth flow (requires ngrok for local development)
ngrok http 8501
# Update X_REDIRECT_URI with ngrok URL
```

### Production Validation
- Check Azure Web App logs for container startup
- Verify Key Vault secret references resolve
- Monitor Application Insights for errors
- Test OAuth flow with production redirect URI
- Verify Functions Timer Trigger execution
- Check Firestore post processing
- Monitor Functions execution logs