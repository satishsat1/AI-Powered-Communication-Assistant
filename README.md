# AI-Powered Communication Assistant

An **AI-driven Email Assistant** built with **Flask** (backend) and a modern **Dashboard UI** (frontend).  
It connects to Gmail (IMAP/SMTP), analyzes emails with **OpenAI GPT** (or fallback keyword rules), stores them in **SQLite**, and provides a smart dashboard with AI-generated response suggestions.

---

## 🚀 Features

- 📧 Fetch Gmail emails securely via IMAP  
- 🤖 Sentiment (Positive / Negative / Neutral) & Priority (Urgent / Normal) analysis  
- 📊 Interactive dashboard with visual charts (Chart.js)  
- ✉️ AI-generated draft responses with one-click send via SMTP  
- 💾 SQLite database for message storage  
- 🔒 Environment-based configuration (no secrets in code)  

---

## 🛠️ Project Structure

AI-Powered-Communication-Assistant/
├─ backend.py # Flask API backend
├─ templates/
│ └─ index.html # Dashboard UI (renamed from code.html)
├─ requirements.txt # Python dependencies
├─ .gitignore # Excludes venv, db, env files
└─ README.md # Project documentation

Create & activate a virtual environment

Windows (PowerShell):

python -m venv .venv
.\.venv\Scripts\Activate.ps1

Create & activate a virtual environment

Windows (PowerShell):

python -m venv .venv
.\.venv\Scripts\Activate.ps1

Install dependencies
pip install -r requirements.txt

Configure environment variables

Create a .env file (or export manually). Required:

EMAIL_USER=your_gmail@gmail.com
EMAIL_PASS=your_app_password      # Use a Gmail App Password (not your real password)
OPENAI_API_KEY=sk-xxxxxxx         # Optional, falls back to keyword rules if missing

Run the backend
python backend.py


Now open 👉 http://localhost:5000
 in your browser to access the dashboard.


 📊 Dashboard Highlights

🔴 Urgent vs Normal email stats

😀 Positive / Negative / Neutral sentiment breakdown

📋 Email list with AI response drafts

📈 Charts powered by Chart.js

✉️ One-click “Send Response” button

🔒 Security Notes

.env, .venv/, and emails.db are excluded via .gitignore.

Use Gmail App Passwords (enable IMAP in Gmail settings).

OpenAI key is optional; fallback analysis works if not provided.
