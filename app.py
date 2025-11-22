# app.py
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import firebase_admin
from firebase_admin import credentials, firestore, auth
import json
import os
from datetime import datetime
import uuid
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')

# Initialize Firebase
try:
    # For Vercel deployment, we'll use environment variables
    firebase_config = {
        "type": os.environ.get('FIREBASE_TYPE'),
        "project_id": os.environ.get('FIREBASE_PROJECT_ID'),
        "private_key_id": os.environ.get('FIREBASE_PRIVATE_KEY_ID'),
        "private_key": os.environ.get('FIREBASE_PRIVATE_KEY').replace('\\n', '\n'),
        "client_email": os.environ.get('FIREBASE_CLIENT_EMAIL'),
        "client_id": os.environ.get('FIREBASE_CLIENT_ID'),
        "auth_uri": os.environ.get('FIREBASE_AUTH_URI'),
        "token_uri": os.environ.get('FIREBASE_TOKEN_URI'),
        "auth_provider_x509_cert_url": os.environ.get('FIREBASE_AUTH_PROVIDER_CERT_URL'),
        "client_x509_cert_url": os.environ.get('FIREBASE_CLIENT_CERT_URL')
    }
    
    cred = credentials.Certificate(firebase_config)
    firebase_admin.initialize_app(cred)
except:
    # For local development, you might use a service account file
    # Make sure to add FIREBASE_CONFIG.json to .gitignore
    if os.path.exists('FIREBASE_CONFIG.json'):
        cred = credentials.Certificate('FIREBASE_CONFIG.json')
        firebase_admin.initialize_app(cred)

db = firestore.client()

@app.route('/landing')
def landing():
    return render_template('landing.html')

@app.route('/')
def index():
    if 'user' in session:
        user_data = session['user']
        if user_data.get('is_admin', False):
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('staff_dashboard'))
    return redirect(url_for('landing'))

# Add these new routes to your app.py

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user' in session:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        user_type = request.form.get('user_type', 'staff')  # staff or admin
        
        # Validation
        if not name or not email or not password:
            return render_template('register.html', error='All fields are required')
        
        if password != confirm_password:
            return render_template('register.html', error='Passwords do not match')
        
        if len(password) < 6:
            return render_template('register.html', error='Password must be at least 6 characters')
        
        try:
            # Check if user already exists
            users_ref = db.collection('users')
            query = users_ref.where('email', '==', email).limit(1)
            results = query.get()
            
            if len(results) > 0:
                return render_template('register.html', error='Email already registered')
            
            # Create new user (in a real app, you'd hash the password)
            user_data = {
                'name': name,
                'email': email,
                'password':  generate_password_hash(password),  # In production, hash this password!
                'is_admin': (user_type == 'admin'),
                'created_at': datetime.now(),
                'active': True
            }
            
            # Add user to database
            new_user_ref = db.collection('users').document()
            new_user_ref.set(user_data)
            
            # Auto-login after registration
            session['user'] = {
                'id': new_user_ref.id,
                'email': email,
                'name': name,
                'is_admin': (user_type == 'admin')
            }
            
            return redirect(url_for('index'))
            
        except Exception as e:
            return render_template('register.html', error=str(e))
    
    return render_template('register.html')

@app.route('/admin/create_user', methods=['GET', 'POST'])
def admin_create_user():
    if 'user' not in session or not session['user'].get('is_admin', False):
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        user_type = request.form.get('user_type', 'staff')
        
        # Validation
        if not name or not email or not password:
            return render_template('admin_create_user.html', error='All fields are required')
        
        try:
            # Check if user already exists
            users_ref = db.collection('users')
            query = users_ref.where('email', '==', email).limit(1)
            results = query.get()
            
            if len(results) > 0:
                return render_template('admin_create_user.html', error='Email already registered')
            
            # Create new user
            user_data = {
                'name': name,
                'email': email,
                'password':  generate_password_hash(password),  # Hash this in production!
                'is_admin': (user_type == 'admin'),
                'created_at': datetime.now(),
                'created_by': session['user']['id'],
                'active': True
            }
            
            db.collection('users').document().set(user_data)
            
            return redirect(url_for('admin_dashboard', message='User created successfully'))
            
        except Exception as e:
            return render_template('admin_create_user.html', error=str(e))
    
    return render_template('admin_create_user.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        try:
            # In a real app, you would verify credentials with Firebase Auth
            # For simplicity, we'll use a direct Firestore check
            users_ref = db.collection('users')
            query = users_ref.where('email', '==', email).limit(1)
            results = query.get()
            
            if len(results) == 0:
                return render_template('login.html', error='Invalid credentials')
            
            user_data = results[0].to_dict()
            # In a real app, you would verify the password hash
            # For demo purposes, we'll assume password is correct
            session['user'] = {
                'id': results[0].id,
                'email': user_data['email'],
                'name': user_data['name'],
                'is_admin': user_data.get('is_admin', False)
            }
            
            return redirect(url_for('index'))
        except Exception as e:
            return render_template('login.html', error=str(e))
    
    return render_template('login.html')

@app.route('/staff/dashboard')
def staff_dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    user_data = session['user']
    if user_data.get('is_admin', False):
        return redirect(url_for('admin_dashboard'))
    
    # Get today's activities
    today = datetime.now().strftime('%Y-%m-%d')
    activities_ref = db.collection('activities')
    query = activities_ref.where('user_id', '==', user_data['id']).where('date', '==', today)
    today_activities = [act.to_dict() for act in query.get()]
    
    # Check if already logged in today
    has_login = any(act['type'] == 'login' for act in today_activities)
    has_logout = any(act['type'] == 'logout' for act in today_activities)
    
    return render_template('staff_dashboard.html', 
                          user=user_data, 
                          has_login=has_login, 
                          has_logout=has_logout,
                          activities=today_activities)

@app.route('/staff/login', methods=['POST'])
def staff_login():
    if 'user' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'})
    
    user_data = session['user']
    if user_data.get('is_admin', False):
        return jsonify({'success': False, 'error': 'Admins cannot perform staff actions'})
    
    try:
        # Get location data
        lat = request.form.get('lat')
        lng = request.form.get('lng')
        location = request.form.get('location', 'Unknown location')
        
        # Handle photo upload
        photo_url = ''
        if 'photo' in request.files:
            photo = request.files['photo']
            if photo.filename != '':
                # In a real app, you would upload to Firebase Storage
                # For demo, we'll just store a reference
                filename = f"login_{user_data['id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                photo_url = f"/uploads/{filename}"
                # Save file locally for demo (not suitable for production)
                photo.save(os.path.join('static', photo_url))
        
        # Create activity record
        activity_id = str(uuid.uuid4())
        activity_data = {
            'id': activity_id,
            'user_id': user_data['id'],
            'user_name': user_data['name'],
            'type': 'login',
            'timestamp': datetime.now(),
            'date': datetime.now().strftime('%Y-%m-%d'),
            'location': location,
            'lat': lat,
            'lng': lng,
            'photo_url': photo_url
        }
        
        db.collection('activities').document(activity_id).set(activity_data)
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/staff/logout', methods=['POST'])
def staff_logout():
    if 'user' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'})
    
    user_data = session['user']
    if user_data.get('is_admin', False):
        return jsonify({'success': False, 'error': 'Admins cannot perform staff actions'})
    
    try:
        # Get location data
        lat = request.form.get('lat')
        lng = request.form.get('lng')
        location = request.form.get('location', 'Unknown location')
        
        # Handle photo upload
        photo_url = ''
        if 'photo' in request.files:
            photo = request.files['photo']
            if photo.filename != '':
                filename = f"logout_{user_data['id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                photo_url = f"/uploads/{filename}"
                photo.save(os.path.join('static', photo_url))
        
        # Create activity record
        activity_id = str(uuid.uuid4())
        activity_data = {
            'id': activity_id,
            'user_id': user_data['id'],
            'user_name': user_data['name'],
            'type': 'logout',
            'timestamp': datetime.now(),
            'date': datetime.now().strftime('%Y-%m-%d'),
            'location': location,
            'lat': lat,
            'lng': lng,
            'photo_url': photo_url
        }
        
        db.collection('activities').document(activity_id).set(activity_data)
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    user_data = session['user']
    if not user_data.get('is_admin', False):
        return redirect(url_for('staff_dashboard'))
    
    # Get all users
    users_ref = db.collection('users')
    users = [{'id': user.id, **user.to_dict()} for user in users_ref.get()]
    
    # Get filter parameters
    filter_user = request.args.get('user', 'all')
    filter_date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    
    # Build query
    activities_ref = db.collection('activities')
    if filter_user != 'all':
        activities_ref = activities_ref.where('user_id', '==', filter_user)
    if filter_date:
        activities_ref = activities_ref.where('date', '==', filter_date)
    
    activities = [act.to_dict() for act in activities_ref.order_by('timestamp').get()]
    
    return render_template('admin_dashboard.html', 
                          user=user_data, 
                          users=users, 
                          activities=activities,
                          filter_user=filter_user,
                          filter_date=filter_date)

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

# Add these imports at the top
from datetime import datetime, timedelta

# Add these routes to your app.py

@app.route('/profile')
def profile():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    user_data = session['user']
    
    # Get user's activity statistics
    activities_ref = db.collection('activities')
    user_activities = activities_ref.where('user_id', '==', user_data['id']).get()
    
    total_logins = sum(1 for act in user_activities if act.to_dict().get('type') == 'login')
    total_logouts = sum(1 for act in user_activities if act.to_dict().get('type') == 'logout')
    
    # Count unique days with activity
    unique_days = set()
    for act in user_activities:
        act_data = act.to_dict()
        if 'date' in act_data:
            unique_days.add(act_data['date'])
    days_active = len(unique_days)
    
    # Get user details from database
    user_ref = db.collection('users').document(user_data['id'])
    user_details = user_ref.get().to_dict()
    
    return render_template('profile.html', 
                          user={**user_data, **user_details},
                          total_logins=total_logins,
                          total_logouts=total_logouts,
                          days_active=days_active)

@app.route('/activity_logs')
def activity_logs():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    user_data = session['user']
    
    # Get all users (for filter dropdown)
    users_ref = db.collection('users')
    users = [{'id': user.id, **user.to_dict()} for user in users_ref.get()]
    
    # Get filter parameters
    filter_user = request.args.get('user', 'all')
    filter_date = request.args.get('date', '')
    filter_type = request.args.get('activity_type', 'all')
    
    # Build query
    activities_ref = db.collection('activities')
    
    if filter_user != 'all':
        activities_ref = activities_ref.where('user_id', '==', filter_user)
    
    if filter_date:
        activities_ref = activities_ref.where('date', '==', filter_date)
    
    if filter_type != 'all':
        activities_ref = activities_ref.where('type', '==', filter_type)
    
    activities = [act.to_dict() for act in activities_ref.order_by('timestamp', direction=firestore.Query.DESCENDING).get()]
    
    # If non-admin tries to view other users' logs, redirect them to their own
    if not user_data.get('is_admin', False) and filter_user != 'all' and filter_user != user_data['id']:
        return redirect(url_for('activity_logs', user=user_data['id']))
    
    return render_template('activity_logs.html', 
                          user=user_data, 
                          users=users, 
                          activities=activities,
                          filter_user=filter_user,
                          filter_date=filter_date,
                          filter_type=filter_type)

# Add this error handler
@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

# Create a simple 404.html template
# templates/404.html
"""
{% extends "base.html" %}

{% block content %}
<div class="error-container">
    <h2>Page Not Found</h2>
    <p>The page you're looking for doesn't exist.</p>
    <a href="{{ url_for('index') }}" class="btn btn-primary">Return to Dashboard</a>
</div>

<style>
.error-container {
    text-align: center;
    padding: 2rem;
    max-width: 500px;
    margin: 0 auto;
}
</style>
{% endblock %}
"""

if __name__ == '__main__':
    app.run(debug=True)