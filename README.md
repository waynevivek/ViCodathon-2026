# AI Interview Agent (ViCodathon 2026)

An AI agent that conducts a multi-turn technical interview with a candidate, personalized to their progress through a 31-day AI Cohort curriculum.

## Local Setup & Running

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment Variables**:
   Create a `.env` file in the root directory:
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   ```

3. **Start Local Development Server**:
   ```bash
   uvicorn main:app --reload --host 127.0.0.1 --port 8000
   ```

4. **Verify Health Endpoint**:
   ```bash
   curl http://127.0.0.1:8000/health
   ```

## Render Deployment Instructions

### Manual Dashboard Deployment
1. Log in to [Render Dashboard](https://dashboard.render.com).
2. Click **New +** -> **Web Service**.
3. Connect your GitHub repository: `ViCodathon-2026`.
4. Configure service settings:
   - **Name**: `vicodathon-ai-interview-agent`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Under **Environment Variables**, add:
   - `GROQ_API_KEY`: *(your Groq API key)*
6. Click **Create Web Service**.

### Blueprint Deployment
Alternatively, link the repository using Render Blueprints; Render will automatically detect `render.yaml`.
