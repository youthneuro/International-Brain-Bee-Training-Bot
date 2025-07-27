# Brain Bee Training Bot

A web-based training platform for International Brain Bee competition preparation. Generates neuroscience questions, tracks progress, and provides detailed feedback.

## Features

- **Question Generation**: AI-powered Brain Bee style multiple-choice questions across neuroscience categories
- **Interactive Quiz**: Real-time feedback with explanations for incorrect answers
- **Progress Tracking**: Session-based history of questions and performance
- **Analytics**: Performance metrics and category-based analysis
- **Persistent Storage**: User data and feedback stored in Supabase
- **Responsive UI**: Clean interface that works on desktop and mobile

## Tech Stack

- **Backend**: Flask (Python)
- **AI**: Azure OpenAI GPT-4
- **Database**: Supabase (PostgreSQL + Storage)
- **Frontend**: HTML, CSS, JavaScript
- **Deployment**: Vercel
- **Session Management**: Flask-Session

## Setup

1. Install dependencies: `pip install -r requirements.txt`
2. Set environment variables:
   - `AZURE_OPENAI_API_KEY`
   - `AZURE_OPENAI_ENDPOINT`
   - `SUPABASE_URL`
   - `SUPABASE_ANON_KEY`
   - `FLASK_SECRET_KEY`
3. Run: `python app.py`

## Categories

- Sensory System
- Motor System
- Neural Communication
- Neuroanatomy
- Higher Cognition
- Neurology (Diseases)

## Deployment

Currently deployed on Vercel with Supabase for data persistence.
