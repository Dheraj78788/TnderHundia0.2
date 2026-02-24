from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from functools import wraps
import firebase_admin
from firebase_admin import credentials, auth, db
import os
import json
from datetime import datetime
import traceback

app = Flask(__name__)
app.secret_key = 'tenderhub-india-firebase-2026-production-key'

# 🔥 FIREBASE INITIALIZATION WITH ERROR HANDLING
try:
    print("🔥 Initializing Firebase...")
    cred = credentials.Certificate("firebase-service-account.json")
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://blink2-c6aae-default-rtdb.asia-southeast1.firebasedatabase.app/'
    })
    print("✅ Firebase initialized successfully!")
except Exception as e:
    print(f"❌ Firebase Error: {e}")
    print("💡 Make sure firebase-service-account.json is in the same folder as app.py")
    firebase_admin_initialized = False
else:
    firebase_admin_initialized = True

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        try:
            # Verify with Firebase Auth
            user = auth.get_user_by_email(email)
            session['user_id'] = user.uid
            session['email'] = email
            
            # Get user data from Firebase Database
            user_ref = db.reference(f'users/{user.uid}').get()
            if user_ref:
                session['name'] = user_ref.get('name', email.split('@')[0])
                session['is_premium'] = user_ref.get('is_premium', False)
            else:
                session['name'] = email.split('@')[0]
                session['is_premium'] = False
            
            flash('✅ Login successful! Welcome to TenderHub India.', 'success')
            return redirect(url_for('profile'))
            
        except auth.UserNotFoundError:
            flash('❌ User not found. Please register first.', 'error')
        except Exception as e:
            flash(f'❌ Login failed: {str(e)}', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        
        try:
            # Create user in Firebase Auth
            user = auth.create_user(email=email, password=password)
            print(f"✅ New user created: {user.uid}")
            
            # Save profile in Firebase Database
            db.reference(f'users/{user.uid}').set({
                'name': name,
                'email': email,
                'is_premium': False,
                'subscription_date': None,
                'created_at': datetime.utcnow().isoformat(),
                'tenders_saved': []
            })
            
            # Auto login
            session['user_id'] = user.uid
            session['email'] = email
            session['name'] = name
            session['is_premium'] = False
            
            flash(f'🎉 Welcome {name}! Account created successfully.', 'success')
            return redirect(url_for('profile'))
            
        except Exception as e:
            error_msg = str(e)
            if "already exists" in error_msg.lower():
                flash('❌ Email already registered. Please login.', 'error')
            else:
                flash(f'❌ Registration failed: {error_msg}', 'error')
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('👋 Logged out successfully!', 'info')
    return redirect(url_for('index'))

@app.route('/profile')
@login_required
def profile():
    try:
        user_id = session['user_id']
        user_ref = db.reference(f'users/{user_id}')
        user_data = user_ref.get() or {}
        
        return render_template('profile.html',
                             user_name=user_data.get('name', session.get('name')),
                             user_email=user_data.get('email', session.get('email')),
                             is_premium=user_data.get('is_premium', False),
                             subscription_date=user_data.get('subscription_date'),
                             created_at=user_data.get('created_at'),
                             tenders_saved=len(user_data.get('tenders_saved', [])))
    except:
        flash('Profile load error. Please login again.', 'error')
        return redirect(url_for('login'))

@app.route('/subscribe', methods=['POST'])
@login_required
def subscribe():
    try:
        user_id = session['user_id']
        db.reference(f'users/{user_id}').update({
            'is_premium': True,
            'subscription_date': datetime.utcnow().isoformat()
        })
        session['is_premium'] = True
        flash('⭐ Premium subscription activated! Full access unlocked!', 'success')
        return redirect(url_for('profile'))
    except Exception as e:
        flash(f'Subscription error: {str(e)}', 'error')
        return redirect(url_for('profile'))

if __name__ == '__main__':
    print("🚀 TenderHub India - Firebase Edition")
    print("📁 Working directory:", os.getcwd())
    print("🔍 Files found:", os.listdir('.'))
    if os.path.exists('firebase-service-account.json'):
        print("✅ firebase-service-account.json FOUND!")
    else:
        print("❌ firebase-service-account.json NOT FOUND!")
    
    app.run(debug=True, port=5000, host='0.0.0.0')
