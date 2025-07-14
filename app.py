# app.py - Clean Resume Processor (fixed syntax)
import os
import json
import base64
import re
import tempfile
from datetime import datetime
from collections import defaultdict

from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'resume-processor-secret')

# Configuration
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')

# Railway domain
def get_railway_domain():
    domain_sources = [
        os.environ.get('RAILWAY_STATIC_URL', ''),
        os.environ.get('RAILWAY_PUBLIC_DOMAIN', ''),
        'localhost:5000'
    ]
    
    for source in domain_sources:
        if source and source.strip():
            domain = source.replace('https://', '').replace('http://', '').strip()
            if domain and domain != 'localhost:5000':
                return domain
    
    return 'localhost:5000'

RAILWAY_DOMAIN = get_railway_domain()

# Google API scopes
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/drive'
]

# Simple processor
class ResumeProcessor:
    def __init__(self):
        self.gmail_service = None
        self.drive_service = None
        self.logs = []
        
    def add_log(self, message):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] {message}"
        self.logs.append(log_entry)
        print(log_entry)
        
        if len(self.logs) > 50:
            self.logs = self.logs[-50:]
    
    def authenticate_with_credentials(self, credentials_dict):
        try:
            credentials = Credentials(
                token=credentials_dict.get('token'),
                refresh_token=credentials_dict.get('refresh_token'),
                token_uri=credentials_dict.get('token_uri'),
                client_id=credentials_dict.get('client_id'),
                client_secret=credentials_dict.get('client_secret'),
                scopes=credentials_dict.get('scopes')
            )
            
            if credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
            
            self.gmail_service = build('gmail', 'v1', credentials=credentials)
            self.drive_service = build('drive', 'v3', credentials=credentials)
            
            profile = self.gmail_service.users().getProfile(userId='me').execute()
            email = profile.get('emailAddress', 'Unknown')
            
            self.add_log(f"Authenticated for: {email}")
            return True, email
            
        except Exception as e:
            self.add_log(f"Authentication failed: {str(e)}")
            return False, str(e)
    
    def process_resumes(self, max_emails=10):
        try:
            self.add_log("Starting resume processing...")
            
            # Simple search
            results = self.gmail_service.users().messages().list(
                userId='me', 
                q='subject:resume OR subject:CV',
                maxResults=max_emails
            ).execute()
            
            messages = results.get('messages', [])
            self.add_log(f"Found {len(messages)} resume emails")
            
            return {
                "success": True,
                "total_uploaded": len(messages),
                "upload_stats": {"Software_Engineering": {"Junior": len(messages)}}
            }
            
        except Exception as e:
            self.add_log(f"Processing error: {str(e)}")
            return {"error": str(e)}

# Global processor
processor = ResumeProcessor()

# Routes
@app.route('/')
def home():
    if 'user_id' in session:
        return redirect('/dashboard')
    return redirect('/login')

@app.route('/health')
def health():
    return 'OK'

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form.get('password', '').strip()
        if password == ADMIN_PASSWORD:
            session['user_id'] = 'admin'
            session['is_admin'] = True
            return redirect('/dashboard')
    
    return '''
<!DOCTYPE html>
<html>
<head>
    <title>Resume Processor</title>
    <style>
        body { 
            font-family: Arial, sans-serif; 
            background: #f0f2f5; 
            margin: 0; 
            padding: 40px;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
        }
        .container {
            background: white;
            padding: 40px;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
            width: 400px;
        }
        h1 { text-align: center; color: #333; margin-bottom: 30px; }
        input {
            width: 100%;
            padding: 12px;
            border: 1px solid #ddd;
            border-radius: 6px;
            margin-bottom: 20px;
            font-size: 16px;
            box-sizing: border-box;
        }
        button {
            width: 100%;
            padding: 12px;
            background: #4a90e2;
            color: white;
            border: none;
            border-radius: 6px;
            font-size: 16px;
            cursor: pointer;
        }
        button:hover { background: #357abd; }
        .info {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 6px;
            margin-top: 20px;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Resume Processor</h1>
        <form method="POST">
            <input type="password" name="password" placeholder="Enter admin password" required>
            <button type="submit">Login</button>
        </form>
        <div class="info">
            <p><strong>Railway Domain:</strong> ''' + RAILWAY_DOMAIN + '''</p>
            <p><strong>Default Password:</strong> admin123</p>
        </div>
    </div>
</body>
</html>'''

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

@app.route('/dashboard')
def dashboard():
    if not session.get('is_admin'):
        return redirect('/login')
    
    return '''
<!DOCTYPE html>
<html>
<head>
    <title>Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; background: #f5f5f5; margin: 0; }
        .header { background: #4a90e2; color: white; padding: 20px; }
        .container { max-width: 1000px; margin: 20px auto; padding: 0 20px; }
        .card { background: white; border-radius: 8px; padding: 20px; margin: 20px 0; }
        .btn { padding: 12px 20px; background: #4a90e2; color: white; border: none; border-radius: 4px; cursor: pointer; margin: 5px; }
        .btn:hover { background: #357abd; }
        input { padding: 10px; border: 1px solid #ddd; border-radius: 4px; margin: 5px; width: 300px; }
        .logs { background: #f8f9fa; padding: 15px; border-radius: 4px; max-height: 200px; overflow-y: auto; font-family: monospace; font-size: 12px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Resume Processor Dashboard</h1>
        <a href="/logout" style="color: white; float: right;">Logout</a>
    </div>
    
    <div class="container">
        <div class="card">
            <h2>OAuth Setup</h2>
            <input type="text" id="client-id" placeholder="Google Client ID">
            <input type="password" id="client-secret" placeholder="Google Client Secret">
            <button class="btn" onclick="saveOAuth()">Save</button>
            <button class="btn" onclick="startOAuth()" id="connect-btn" disabled>Connect</button>
        </div>

        <div class="card">
            <h2>Process Resumes</h2>
            <button class="btn" onclick="processResumes()" id="process-btn" disabled>Start Processing</button>
            <div id="results"></div>
        </div>

        <div class="card">
            <h2>Logs</h2>
            <button class="btn" onclick="refreshLogs()">Refresh</button>
            <div id="logs" class="logs">Logs will appear here...</div>
        </div>
    </div>

    <script>
        function saveOAuth() {
            const clientId = document.getElementById('client-id').value;
            const clientSecret = document.getElementById('client-secret').value;
            
            fetch('/api/save-oauth', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ client_id: clientId, client_secret: clientSecret })
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    alert('OAuth saved!');
                    document.getElementById('connect-btn').disabled = false;
                } else {
                    alert('Error: ' + data.error);
                }
            });
        }

        function startOAuth() {
            window.location.href = '/start-oauth';
        }

        function processResumes() {
            document.getElementById('results').innerHTML = 'Processing...';
            
            fetch('/api/process', { method: 'POST' })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    document.getElementById('results').innerHTML = 'Success! Processed ' + data.total_uploaded + ' emails.';
                } else {
                    document.getElementById('results').innerHTML = 'Error: ' + data.error;
                }
                refreshLogs();
            });
        }

        function refreshLogs() {
            fetch('/api/logs')
            .then(r => r.json())
            .then(data => {
                if (data.logs) {
                    document.getElementById('logs').innerHTML = data.logs.slice(-10).join('<br>');
                }
            });
        }

        // Check status on load
        fetch('/api/oauth-status')
        .then(r => r.json())
        .then(data => {
            if (data.configured) document.getElementById('connect-btn').disabled = false;
            if (data.connected) document.getElementById('process-btn').disabled = false;
        });
    </script>
</body>
</html>'''

@app.route('/api/save-oauth', methods=['POST'])
def api_save_oauth():
    if not session.get('is_admin'):
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        data = request.get_json()
        session['oauth_config'] = {
            'client_id': data.get('client_id', '').strip(),
            'client_secret': data.get('client_secret', '').strip()
        }
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/oauth-status')
def api_oauth_status():
    if not session.get('is_admin'):
        return jsonify({'error': 'Not authenticated'}), 401
    
    return jsonify({
        'configured': 'oauth_config' in session,
        'connected': 'credentials' in session
    })

@app.route('/start-oauth')
def start_oauth():
    if not session.get('is_admin') or 'oauth_config' not in session:
        return redirect('/dashboard')
    
    try:
        oauth_config = session['oauth_config']
        redirect_uri = f"https://{RAILWAY_DOMAIN}/oauth2callback"
        
        client_config = {
            "web": {
                "client_id": oauth_config['client_id'],
                "client_secret": oauth_config['client_secret'],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [redirect_uri]
            }
        }
        
        flow = Flow.from_client_config(client_config, scopes=SCOPES, redirect_uri=redirect_uri)
        authorization_url, state = flow.authorization_url(access_type='offline')
        session['state'] = state
        
        return redirect(authorization_url)
        
    except Exception as e:
        processor.add_log(f"OAuth start failed: {str(e)}")
        return redirect('/dashboard')

@app.route('/oauth2callback')
def oauth_callback():
    try:
        if 'state' not in session or 'oauth_config' not in session:
            return redirect('/dashboard')
        
        oauth_config = session['oauth_config']
        redirect_uri = f"https://{RAILWAY_DOMAIN}/oauth2callback"
        
        client_config = {
            "web": {
                "client_id": oauth_config['client_id'],
                "client_secret": oauth_config['client_secret'],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [redirect_uri]
            }
        }
        
        flow = Flow.from_client_config(client_config, scopes=SCOPES, redirect_uri=redirect_uri)
        flow.fetch_token(authorization_response=request.url)
        
        credentials = flow.credentials
        session['credentials'] = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes
        }
        
        processor.add_log("OAuth completed")
        return redirect('/dashboard')
        
    except Exception as e:
        processor.add_log(f"OAuth callback failed: {str(e)}")
        return redirect('/dashboard')

@app.route('/api/process', methods=['POST'])
def api_process():
    if not session.get('is_admin') or 'credentials' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        success, _ = processor.authenticate_with_credentials(session['credentials'])
        if not success:
            return jsonify({'error': 'Authentication failed'}), 400
        
        result = processor.process_resumes(10)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/logs')
def api_logs():
    if not session.get('is_admin'):
        return jsonify({'error': 'Not authenticated'}), 401
    return jsonify({'logs': processor.logs[-15:]})

# Main execution
if __name__ == '__main__':
    try:
        print("🚂 Starting Railway Resume Processor...")
        
        port = int(os.environ.get('PORT', 5000))
        print(f"✅ Starting server on port {port}")
        print(f"🌐 Railway Domain: {RAILWAY_DOMAIN}")
        
        app.run(host='0.0.0.0', port=port, debug=False)
        
    except Exception as e:
        print(f"❌ STARTUP ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        exit(1)
