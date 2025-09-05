#!/usr/bin/env python3
"""
AI-Powered Communication Assistant - Backend API
Complete implementation with email processing, AI analysis, and response generation
"""

from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import imaplib
import email
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import sqlite3
import openai
from datetime import datetime, timedelta
import re
import json
import os
from typing import List, Dict, Tuple

app = Flask(__name__)
CORS(app)

# Configuration
class Config:
    # Email Configuration
    IMAP_SERVER = "imap.gmail.com"
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    EMAIL_USER = os.getenv("EMAIL_USER")  # your-email@gmail.com
    EMAIL_PASS = os.getenv("EMAIL_PASS")  # your-app-password
    
    # OpenAI Configuration
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    
    # Database
    DATABASE = "emails.db"
    
    # Support Keywords
    SUPPORT_KEYWORDS = ["support", "query", "request", "help", "issue", "problem"]
    URGENT_KEYWORDS = ["urgent", "critical", "immediate", "emergency", "asap", 
                      "cannot access", "down", "blocked", "failed", "error"]

# Initialize OpenAI
openai.api_key = Config.OPENAI_API_KEY

class EmailProcessor:
    """Core email processing and AI analysis"""
    
    def __init__(self):
        self.init_database()
    
    def init_database(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(Config.DATABASE)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS emails (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender TEXT,
                subject TEXT,
                body TEXT,
                sent_date TEXT,
                sentiment TEXT,
                priority TEXT,
                extracted_info TEXT,
                ai_response TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def connect_email(self) -> imaplib.IMAP4_SSL:
        """Connect to email server"""
        try:
            mail = imaplib.IMAP4_SSL(Config.IMAP_SERVER)
            mail.login(Config.EMAIL_USER, Config.EMAIL_PASS)
            return mail
        except Exception as e:
            print(f"Email connection error: {e}")
            return None
    
    def fetch_emails(self, days_back: int = 1) -> List[Dict]:
        """Fetch emails from the last N days"""
        mail = self.connect_email()
        if not mail:
            return []
        
        try:
            mail.select('inbox')
            
            # Calculate date range
            since_date = (datetime.now() - timedelta(days=days_back)).strftime("%d-%b-%Y")
            
            # Search for emails
            _, message_ids = mail.search(None, f'SINCE "{since_date}"')
            
            emails = []
            for msg_id in message_ids[0].split():
                _, msg_data = mail.fetch(msg_id, '(RFC822)')
                email_body = msg_data[0][1]
                email_message = email.message_from_bytes(email_body)
                
                # Extract email details
                sender = email_message['From']
                subject = email_message['Subject'] or ""
                
                # Get email body
                body = self.extract_email_body(email_message)
                
                # Filter support emails
                if self.is_support_email(subject, body):
                    emails.append({
                        'sender': sender,
                        'subject': subject,
                        'body': body,
                        'sent_date': email_message['Date']
                    })
            
            mail.close()
            mail.logout()
            return emails
            
        except Exception as e:
            print(f"Error fetching emails: {e}")
            return []
    
    def extract_email_body(self, email_message) -> str:
        """Extract plain text from email"""
        if email_message.is_multipart():
            for part in email_message.walk():
                if part.get_content_type() == "text/plain":
                    return part.get_payload(decode=True).decode('utf-8', errors='ignore')
        else:
            return email_message.get_payload(decode=True).decode('utf-8', errors='ignore')
        return ""
    
    def is_support_email(self, subject: str, body: str) -> bool:
        """Check if email is support-related"""
        text = (subject + " " + body).lower()
        return any(keyword in text for keyword in Config.SUPPORT_KEYWORDS)
    
    def analyze_sentiment(self, text: str) -> str:
        """Analyze sentiment using AI"""
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Analyze the sentiment of the following text. Respond with only: positive, negative, or neutral"},
                    {"role": "user", "content": text}
                ],
                max_tokens=10
            )
            return response.choices[0].message.content.strip().lower()
        except:
            # Fallback to keyword-based analysis
            positive_words = ['good', 'great', 'excellent', 'happy', 'satisfied', 'love', 'amazing']
            negative_words = ['bad', 'terrible', 'frustrated', 'angry', 'disappointed', 'problem', 'issue', 'cannot', 'unable']
            
            text_lower = text.lower()
            positive_count = sum(1 for word in positive_words if word in text_lower)
            negative_count = sum(1 for word in negative_words if word in text_lower)
            
            if negative_count > positive_count:
                return 'negative'
            elif positive_count > negative_count:
                return 'positive'
            return 'neutral'
    
    def determine_priority(self, subject: str, body: str) -> str:
        """Determine email priority"""
        text = (subject + " " + body).lower()
        return 'urgent' if any(keyword in text for keyword in Config.URGENT_KEYWORDS) else 'normal'
    
    def extract_key_info(self, email_data: Dict) -> List[str]:
        """Extract key information from email"""
        info = []
        text = email_data['subject'] + " " + email_data['body']
        
        # Extract emails
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails_found = re.findall(email_pattern, text)
        if emails_found:
            info.append(f"Contact: {', '.join(emails_found)}")
        
        # Extract phone numbers
        phone_pattern = r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'
        phones = re.findall(phone_pattern, text)
        if phones:
            info.append(f"Phone: {', '.join(phones)}")
        
        # Categorize request type
        text_lower = text.lower()
        if 'billing' in text_lower or 'payment' in text_lower:
            info.append('Request Type: Billing Issue')
        elif 'login' in text_lower or 'account' in text_lower:
            info.append('Request Type: Account Access')
        elif 'integration' in text_lower or 'api' in text_lower:
            info.append('Request Type: Technical Integration')
        elif 'refund' in text_lower:
            info.append('Request Type: Refund Request')
        elif 'pricing' in text_lower:
            info.append('Request Type: Pricing Inquiry')
        else:
            info.append('Request Type: General Support')
        
        return info if info else ['Request Type: General Support']
    
    def generate_ai_response(self, email_data: Dict, sentiment: str, priority: str) -> str:
        """Generate AI response using OpenAI"""
        try:
            prompt = f"""
            Generate a professional customer support email response for the following:
            
            Customer Email:
            From: {email_data['sender']}
            Subject: {email_data['subject']}
            Content: {email_data['body']}
            
            Context:
            - Sentiment: {sentiment}
            - Priority: {priority}
            
            Guidelines:
            - Be professional and empathetic
            - Address the customer's concern directly
            - If sentiment is negative, acknowledge frustration
            - If priority is urgent, emphasize immediate action
            - Include next steps and timeline
            - Add a case number
            
            Generate only the email response:
            """
            
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"AI response generation error: {e}")
            # Fallback response
            return self.generate_fallback_response(email_data, sentiment, priority)
    
    def generate_fallback_response(self, email_data: Dict, sentiment: str, priority: str) -> str:
        """Generate fallback response without AI"""
        sender_name = email_data['sender'].split('@')[0].replace('<', '').replace('>', '')
        case_number = f"CS{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        if priority == 'urgent' and sentiment == 'negative':
            return f"""Dear {sender_name},

Thank you for reaching out, and I sincerely apologize for the inconvenience you're experiencing. I understand how critical this situation is for you.

I've escalated your case as urgent and our priority support team is now handling your request. We're treating this as a high-priority issue and will work to resolve it as quickly as possible.

You can expect an update within the next 2 hours with a resolution or detailed action plan.

Case Number: {case_number}

Best regards,
AI Support Assistant"""
        
        else:
            timeline = "2 hours" if priority == 'urgent' else "24 hours"
            return f"""Dear {sender_name},

Thank you for contacting our support team. I've received your inquiry and our team is reviewing your request.

{'Given the urgent nature of your request, ' if priority == 'urgent' else ''}We'll provide you with a comprehensive response within {timeline}.

Case Number: {case_number}

Best regards,
AI Support Assistant"""
    
    def process_emails(self, emails: List[Dict]) -> List[Dict]:
        """Process emails with AI analysis"""
        processed_emails = []
        
        for email_data in emails:
            # AI Analysis
            sentiment = self.analyze_sentiment(email_data['subject'] + " " + email_data['body'])
            priority = self.determine_priority(email_data['subject'], email_data['body'])
            extracted_info = self.extract_key_info(email_data)
            ai_response = self.generate_ai_response(email_data, sentiment, priority)
            
            processed_email = {
                **email_data,
                'sentiment': sentiment,
                'priority': priority,
                'extracted_info': extracted_info,
                'ai_response': ai_response
            }
            
            # Save to database
            self.save_email(processed_email)
            processed_emails.append(processed_email)
        
        # Sort by priority (urgent first)
        return sorted(processed_emails, key=lambda x: (x['priority'] != 'urgent', x['sent_date']))
    
    def save_email(self, email_data: Dict):
        """Save processed email to database"""
        conn = sqlite3.connect(Config.DATABASE)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO emails (sender, subject, body, sent_date, sentiment, priority, 
                              extracted_info, ai_response)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            email_data['sender'],
            email_data['subject'],
            email_data['body'],
            email_data['sent_date'],
            email_data['sentiment'],
            email_data['priority'],
            json.dumps(email_data['extracted_info']),
            email_data['ai_response']
        ))
        
        conn.commit()
        conn.close()
    
    def send_email_response(self, to_email: str, subject: str, response: str) -> bool:
        """Send email response via SMTP"""
        try:
            msg = MIMEMultipart()
            msg['From'] = Config.EMAIL_USER
            msg['To'] = to_email
            msg['Subject'] = f"Re: {subject}"
            
            msg.attach(MIMEText(response, 'plain'))
            
            server = smtplib.SMTP(Config.SMTP_SERVER, Config.SMTP_PORT)
            server.starttls()
            server.login(Config.EMAIL_USER, Config.EMAIL_PASS)
            text = msg.as_string()
            server.sendmail(Config.EMAIL_USER, to_email, text)
            server.quit()
            
            return True
            
        except Exception as e:
            print(f"Error sending email: {e}")
            return False

# API Endpoints
processor = EmailProcessor()

@app.route('/')
def index():
    """Serve the main dashboard"""
    return render_template('index.html')

@app.route('/api/fetch-emails', methods=['GET'])
def fetch_emails():
    """Fetch and process new emails"""
    try:
        days_back = request.args.get('days', 1, type=int)
        emails = processor.fetch_emails(days_back)
        processed_emails = processor.process_emails(emails)
        
        # Generate statistics
        stats = {
            'total': len(processed_emails),
            'urgent': len([e for e in processed_emails if e['priority'] == 'urgent']),
            'normal': len([e for e in processed_emails if e['priority'] == 'normal']),
            'positive': len([e for e in processed_emails if e['sentiment'] == 'positive']),
            'negative': len([e for e in processed_emails if e['sentiment'] == 'negative']),
            'neutral': len([e for e in processed_emails if e['sentiment'] == 'neutral'])
        }
        
        return jsonify({
            'success': True,
            'emails': processed_emails,
            'stats': stats
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/send-response', methods=['POST'])
def send_response():
    """Send AI-generated response"""
    try:
        data = request.json
        recipient = data['recipient']
        subject = data['subject']
        response = data['response']
        
        success = processor.send_email_response(recipient, subject, response)
        
        if success:
            # Update database status
            conn = sqlite3.connect(Config.DATABASE)
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE emails SET status = 'sent' WHERE sender = ? AND subject = ?",
                (recipient, subject)
            )
            conn.commit()
            conn.close()
        
        return jsonify({'success': success})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/analytics', methods=['GET'])
def get_analytics():
    """Get analytics data"""
    try:
        conn = sqlite3.connect(Config.DATABASE)
        cursor = conn.cursor()
        
        # Get recent emails
        cursor.execute('''
            SELECT sentiment, priority, status, created_at 
            FROM emails 
            WHERE created_at >= datetime('now', '-7 days')
        ''')
        
        results = cursor.fetchall()
        conn.close()
        
        # Process analytics
        analytics = {
            'sentiment_distribution': {
                'positive': len([r for r in results if r[0] == 'positive']),
                'negative': len([r for r in results if r[0] == 'negative']),
                'neutral': len([r for r in results if r[0] == 'neutral'])
            },
            'priority_distribution': {
                'urgent': len([r for r in results if r[1] == 'urgent']),
                'normal': len([r for r in results if r[1] == 'normal'])
            },
            'status_distribution': {
                'pending': len([r for r in results if r[2] == 'pending']),
                'sent': len([r for r in results if r[2] == 'sent'])
            }
        }
        
        return jsonify(analytics)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })

if __name__ == '__main__':
    print("🚀 AI Communication Assistant API Server")
    print("📧 Email Integration: Ready")
    print("🤖 AI Processing: Enabled")
    print("📊 Analytics: Active")
    print("\n🌐 Starting server on http://localhost:5000")
    
    app.run(debug=True, host='0.0.0.0', port=5000)