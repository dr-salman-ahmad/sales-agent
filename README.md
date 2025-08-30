# Sales Automation Agent

An AI-powered sales automation agent built with Google ADK and MCP integration that replicates advanced n8n workflow functionality for lead generation, enrichment, qualification, and personalized outreach.

## 🚀 Features

- **Lead Prospecting**: Find companies using Azure Logic App integration
- **Lead Enrichment**: Gather emails, company insights, and background data
- **Lead Qualification**: Score leads against your ICP (Ideal Customer Persona)
- **Email Personalization**: Generate personalized email content and send via Gmail
- **User-Specific CRM**: Each user works with their own Airtable workspace
- **Multi-User Support**: Handle multiple users with separate credentials
- **OAuth Integration**: Secure Gmail and Airtable authentication
- **Real-time Processing**: Fast, parallel processing of leads

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   FastAPI App   │────│  Root Agent      │────│  MCP Servers    │
│                 │    │  (Orchestrator)  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       ├─ Azure Logic App
         │                       │                       ├─ Hunter.io
         │                       │                       ├─ Airtable CRM
         │                       │                       ├─ Gmail Sender
         │                       │                       ├─ Web Scraper
         │                       │                       └─ OpenAI Client
         │                       │
         │              ┌────────┴────────┐
         │              │  Specialized    │
         │              │  Agents         │
         │              │                 │
         │              ├─ Prospecting    │
         │              ├─ Enrichment     │
         │              ├─ Scoring        │
         │              └─ Personalization│
         │
    ┌────┴────┐
    │ Supabase│
    │ (User   │
    │ Creds)  │
    └─────────┘
```

## 📋 Prerequisites

- Python 3.12+
- Node.js 18+ (for MCP servers)
- Google Cloud Project with Vertex AI enabled
- Supabase account for user credential storage
- API keys for external services

## 🛠️ Installation

### 1. Clone and Setup

```bash
git clone <repository-url>
cd sales-automation-agent

# Copy environment template
cp env.example .env
```

### 2. Configure Environment Variables

Edit `.env` file with your credentials:

```bash
# Google Cloud
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
STAGING_BUCKET=your-staging-bucket
GOOGLE_APPLICATION_CREDENTIALS=./google-cred.json

# External APIs
AZURE_LOGIC_APP_URL=your-azure-logic-app-url
HUNTER_API_KEY=your-hunter-io-api-key
OPENAI_API_KEY=your-openai-api-key

# OAuth Credentials
GMAIL_CLIENT_ID=your-gmail-client-id
GMAIL_CLIENT_SECRET=your-gmail-client-secret
AIRTABLE_CLIENT_ID=your-airtable-client-id
AIRTABLE_CLIENT_SECRET=your-airtable-client-secret

# Database
SUPABASE_URL=your-supabase-url
SUPABASE_KEY=your-supabase-key
```

### 3. Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install Node.js MCP servers
npm install -g @modelcontextprotocol/server-filesystem
npm install -g @modelcontextprotocol/server-sqlite
npm install -g @modelcontextprotocol/server-brave-search
npm install -g @modelcontextprotocol/server-github
```

### 4. Setup Google Cloud Credentials

```bash
# Download your Google Cloud service account key
# Save it as google-cred.json in the project root
```

## 🚀 Usage

### Local Development

```bash
# Run the FastAPI application
python main.py

# Or with uvicorn
uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```

### Testing the Agent

```bash
# Interactive testing
python deployment/run.py

# Run automated tests
python -m pytest tests/ -v
```

### API Endpoints

#### Main Chat Interface
```bash
POST /chat
{
    "user_id": "user-123",
    "message": "Find 5 healthtech companies in Toronto with 50+ employees",
    "user_email": "user@example.com"
}
```

#### Dedicated Endpoints
```bash
# Prospecting
POST /prospect
{
    "user_id": "user-123",
    "message": "Find companies in healthcare industry"
}

# Enrichment
POST /enrich
{
    "user_id": "user-123"
}

# Qualification
POST /qualify
{
    "user_id": "user-123"
}

# Personalization
POST /personalize
{
    "user_id": "user-123",
    "parameters": {"send_emails": true}
}
```

## 🐳 Docker Deployment

### Build and Run

```bash
# Build Docker image
docker build -t sales-automation-agent .

# Run container
docker run -d \
  --name sales-agent \
  -p 8080:8080 \
  --env-file .env \
  -v $(pwd)/google-cred.json:/app/google-cred.json:ro \
  sales-automation-agent
```

### Docker Compose

```bash
# Create docker-compose.yml
cat > docker-compose.yml << 'EOF'
version: '3.8'
services:
  sales-agent:
    build: .
    ports:
      - "8080:8080"
    env_file:
      - .env
    volumes:
      - ./google-cred.json:/app/google-cred.json:ro
    restart: unless-stopped
EOF

# Deploy
docker-compose up -d
```

## ☁️ Cloud Deployment

### Vertex AI Agent Engine

```bash
# Deploy to Vertex AI
python deployment/deploy.py
```

### Google Cloud Run

```bash
# Build and push to Container Registry
docker build -t gcr.io/${GOOGLE_CLOUD_PROJECT}/sales-automation-agent .
docker push gcr.io/${GOOGLE_CLOUD_PROJECT}/sales-automation-agent

# Deploy to Cloud Run
gcloud run deploy sales-automation-agent \
  --image gcr.io/${GOOGLE_CLOUD_PROJECT}/sales-automation-agent \
  --platform managed \
  --region ${GOOGLE_CLOUD_LOCATION} \
  --allow-unauthenticated
```

## 📊 Workflow Examples

### 1. Complete Lead Generation Workflow

```bash
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user-123",
    "message": "Find 5 healthtech companies in Toronto, enrich them, qualify against my ICP, and create personalized emails"
  }'
```

### 2. Step-by-Step Process

```bash
# Step 1: Prospect
curl -X POST http://localhost:8080/prospect \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user-123",
    "message": "Find 10 SaaS companies in San Francisco with 100+ employees"
  }'

# Step 2: Enrich
curl -X POST http://localhost:8080/enrich \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user-123"}'

# Step 3: Qualify
curl -X POST http://localhost:8080/qualify \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user-123"}'

# Step 4: Personalize and Send
curl -X POST http://localhost:8080/personalize \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user-123",
    "parameters": {"send_emails": true}
  }'
```

## 🔧 Configuration

### Supabase Database Schema

Required tables:

```sql
-- OAuth connections
CREATE TABLE oauth_connections (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    provider_email TEXT NOT NULL,
    access_token TEXT NOT NULL,
    refresh_token TEXT NOT NULL,
    token_expires_at TIMESTAMP NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- User profiles
CREATE TABLE profiles (
    id TEXT PRIMARY KEY,
    email TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### Airtable CRM Structure

Each user needs a "Sales Agent CRM" base with:

**Demo Table (Leads):**
- UUID (Single line text)
- Name (Single line text)
- Website (URL)
- Email (Email)
- Phone (Phone number)
- Industry (Single line text)
- Company Size (Single line text)
- Address (Long text)
- LinkedIn (URL)
- Background (Long text)
- Score (Single select: Hot, Warm, Cold)
- Personalized Opener (Long text)
- Enriched (Checkbox)

**Personas Table (ICP):**
- User ID (Single line text)
- Name (Single line text)
- Target Industries (Multiple select)
- Company Size Range (Single line text)
- Job Titles (Multiple select)
- Pain Points (Multiple select)
- Use Cases (Multiple select)

## 🧪 Testing

### Unit Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_agents.py -v

# Run with coverage
python -m pytest tests/ --cov=. --cov-report=html
```

### Integration Tests

```bash
# Run integration tests (requires full environment)
python -m pytest tests/ -v -m integration
```

### Manual Testing

```bash
# Interactive testing mode
python deployment/run.py

# Test specific workflows
python -c "
import asyncio
from agents.root_agent import sales_orchestrator

async def test():
    response = await sales_orchestrator.process_request(
        user_id='test-user',
        message='Find 3 tech companies in NYC'
    )
    print(response)

asyncio.run(test())
"
```

## 📚 API Documentation

### Response Format

All endpoints return a consistent response format:

```json
{
    "success": true,
    "message": "Operation completed successfully",
    "leads_processed": 5,
    "data": {
        "task_type": "prospecting",
        "additional_info": "..."
    },
    "errors": null
}
```

### Error Handling

- **400**: Bad Request (missing parameters)
- **401**: Unauthorized (invalid credentials)
- **404**: Not Found (user/resource not found)
- **500**: Internal Server Error

## 🔒 Security

- OAuth 2.0 for Gmail and Airtable authentication
- Automatic token refresh
- User data isolation
- Non-root Docker container
- Environment variable protection
- Input validation and sanitization

## 🚨 Troubleshooting

### Common Issues

1. **MCP Server Connection Failed**
   ```bash
   # Check Node.js installation
   node --version
   npm --version
   
   # Reinstall MCP servers
   npm install -g @modelcontextprotocol/server-filesystem
   ```

2. **Google Cloud Authentication**
   ```bash
   # Verify credentials
   gcloud auth application-default login
   
   # Check service account
   export GOOGLE_APPLICATION_CREDENTIALS=./google-cred.json
   ```

3. **Database Connection Issues**
   ```bash
   # Test Supabase connection
   python -c "
   from utils.supabase_client import supabase_client
   print('Supabase connected successfully')
   "
   ```

### Logs and Monitoring

```bash
# View application logs
docker logs sales-agent -f

# Check health status
curl http://localhost:8080/health

# Monitor performance
docker stats sales-agent
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:

1. Check the troubleshooting section
2. Review the logs for error details
3. Test with the interactive mode
4. Create an issue with detailed information

## 🔄 Updates and Maintenance

### Updating Dependencies

```bash
# Update Python packages
pip install --upgrade -r requirements.txt

# Update MCP servers
npm update -g @modelcontextprotocol/server-filesystem
```

### Monitoring and Alerts

Set up monitoring for:
- API response times
- Error rates
- Token expiration
- Lead processing success rates
- External API quotas

---

**Built with ❤️ using Google ADK and MCP**
