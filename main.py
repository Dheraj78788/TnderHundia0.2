from flask import Flask, render_template, send_from_directory, jsonify, request, session, redirect, url_for
import json
import os
import firebase_admin
from firebase_admin import credentials, auth, firestore
from functools import wraps
from datetime import datetime, timedelta

app = Flask(__name__, static_folder='static', static_url_path='')
app.secret_key = 'tenderhub-super-secret-key-2026'

# 🔥 Initialize Firebase Admin SDK
if not firebase_admin._apps:
    cred = credentials.Certificate('service-account.json')
    firebase_admin.initialize_app(cred, {
        'projectId': 'blink-c30fa',
        'databaseURL': 'https://blink-c30fa-default-rtdatasia-southeast1.firebasedatabase.app/'
    })
db = firestore.client()

# 🔥 ADMIN AUTHENTICATION - Simple password protection
ADMIN_PASSWORD = "admin123"  # Change this in production!

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if auth_header == f'Basic {ADMIN_PASSWORD}':
            return f(*args, **kwargs)
        
        # Also check query param for demo
        if request.args.get('admin_key') == ADMIN_PASSWORD:
            return f(*args, **kwargs)
        
        return jsonify({'error': 'Admin access required'}), 403
    return decorated_function

# 🔥 Regular user login_required (unchanged)
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        token = None
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split('Bearer ')[1]
            try:
                decoded_token = auth.verify_id_token(token)
                uid = decoded_token['uid']
                session['uid'] = uid
                return f(*args, **kwargs, current_user_uid=uid)
            except:
                pass
        
        cookie_token = request.cookies.get('auth_token')
        if cookie_token:
            try:
                if cookie_token.startswith('demo_'):
                    uid = cookie_token.replace('demo_', '')
                    session['uid'] = uid
                    return f(*args, **kwargs, current_user_uid=uid)
            except:
                pass
        
        return jsonify({'error': 'Authentication required'}), 401
    return decorated_function

# 🔥 Static file routes
@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/free-tenders')
def free_tenders():
    return send_from_directory('static', 'tenders.html')

@app.route('/tenders')
def tenders():
    token = request.cookies.get('auth_token')
    if not token:
        return redirect('/free-tenders')
    
    try:
        if token.startswith('demo_'):
            uid = token.replace('demo_', '')
        else:
            decoded_token = auth.verify_id_token(token)
            uid = decoded_token['uid']
        
        user_doc = db.collection('users').document(uid).get()
        if user_doc.exists:
            data = user_doc.to_dict()
            plan = data.get('plan', 'free')
            expiry = data.get('subscription_end')
            if plan == 'pro' and expiry and datetime.fromisoformat(expiry) > datetime.now():
                return send_from_directory('static', 'tenders.html')
        return redirect('/free-tenders')
    except:
        return redirect('/free-tenders')

@app.route('/subscription')
def subscription():
    return send_from_directory('static', 'subscription.html')

@app.route('/auth')
def auth_page():
    return send_from_directory('static', 'auth.html')

@app.route('/profile')
def profile():
    return send_from_directory('static', 'profile.html')

@app.route('/favorites')
def favorites():
    return send_from_directory('static', 'favorites.html')

@app.route('/about')
def about():
    return send_from_directory('static', 'about.html')


@app.route('/premium')
def premium():
    return redirect('/subscription')



# 🔥 ADD THESE TWO ROUTES (put anywhere before if __name__ == '__main__':)

@app.route('/admin-login')
def admin_login_page():
    """Serve admin login page"""
    return send_from_directory('static', 'admin-login.html')

@app.route('/admin')
def admin_panel():
    """Serve admin panel - no auth check for simplicity"""
    return send_from_directory('static', 'admin.html')





# 🔥 ADMIN APIs - Full access to ALL data
@app.route('/api/admin/users', methods=['GET'])
@admin_required
def admin_get_users():
    """Get ALL users from Firebase"""
    try:
        users = db.collection('users').stream()
        user_list = []
        
        for user in users:
            user_data = user.to_dict()
            user_data['uid'] = user.id
            # Add auth user info
            try:
                firebase_user = auth.get_user(user.id)
                user_data['email'] = firebase_user.email
                user_data['displayName'] = firebase_user.display_name or user_data.get('displayName', 'N/A')
            except:
                user_data['email'] = user_data.get('email', 'N/A')
                user_data['displayName'] = user_data.get('displayName', 'N/A')
            
            user_list.append(user_data)
        
        return jsonify(user_list)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/users/<uid>/make-pro', methods=['POST'])
@admin_required
def admin_make_pro(uid):
    """Make any user Pro instantly"""
    try:
        expiry = datetime.utcnow() + timedelta(days=365*2)  # 2 years
        db.collection('users').document(uid).set({
            'plan': 'pro',
            'isPro': True,
            'subscription_status': 'active',
            'subscription_start': datetime.utcnow().isoformat(),
            'subscription_end': expiry.isoformat(),
            'isAdminUpgraded': True
        }, merge=True)
        
        return jsonify({'success': True, 'message': f'User {uid} upgraded to Pro'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/stats', methods=['GET'])
@admin_required
def admin_stats():
    """Admin dashboard stats"""
    try:
        # Users stats
        users = db.collection('users').stream()
        total_users = 0
        pro_users = 0
        
        for user in users:
            total_users += 1
            data = user.to_dict()
            if data.get('plan') == 'pro' and data.get('subscription_end'):
                if datetime.fromisoformat(data['subscription_end']) > datetime.now():
                    pro_users += 1
        
        # Tenders stats
        tenders_stats = {
            'total_portals': 0,
            'total_orgs': 0,
            'total_tenders': 0
        }
        
        if os.path.exists('scrapers/tenders_all3.json'):
            with open('scrapers/tenders_all3.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                for site in data:
                    tenders_stats['total_portals'] += 1
                    for org in site.get('data', []):
                        tenders_stats['total_orgs'] += 1
                        tenders_stats['total_tenders'] += len(org.get('tenders', []))
        
        return jsonify({
            'users': {
                'total': total_users,
                'pro': pro_users
            },
            'tenders': tenders_stats
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 🔥 Regular Tenders API (unchanged)
@app.route('/api/tenders')
def api_tenders():
    token = request.cookies.get('auth_token')
    user_id = request.args.get('userId')
    
    try:
        with open('scrapers/tenders_all3.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Hide Tender ID for free users
        if token and user_id:
            uid = token.replace('demo_', '') if token.startswith('demo_') else user_id
            user_doc = db.collection('users').document(uid).get()
            if not user_doc.exists or user_doc.to_dict().get('plan', 'free') != 'pro':
                for site in data:
                    for org in site['data']:
                        for tender in org['tenders']:
                            if 'details' in tender and 'basic_details' in tender['details']:
                                tender['details']['basic_details'].pop('Tender ID', None)
        
        return jsonify(data)
    except FileNotFoundError:
        return jsonify({"error": "Tenders data not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/scrapers/<path:filename>')
def serve_scrapers(filename):
    return send_from_directory('scrapers', filename)

# 🔥 Subscription APIs (unchanged)
@app.route("/api/subscription/status")
def subscription_status():
    try:
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return jsonify({"isPro": False})

        token = auth_header.split("Bearer ")[1]
        decoded = auth.verify_id_token(token)
        uid = decoded["uid"]

        doc = db.collection("users").document(uid).get()
        if not doc.exists:
            return jsonify({"isPro": False})

        data = doc.to_dict()
        return jsonify({
            "isPro": data.get("isPro", False),
            "plan": data.get("plan", "free"),
            "expiryDate": data.get("subscription_end")
        })
    except Exception as e:
        print("STATUS ERROR:", e)
        return jsonify({"isPro": False})

@app.route("/api/subscription/create", methods=["POST"])
def create_subscription():
    try:
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return jsonify({"error": "Authentication required"}), 401

        token = auth_header.split("Bearer ")[1]
        decoded = auth.verify_id_token(token)
        uid = decoded["uid"]

        data = request.json or {}
        plan = data.get("plan", "pro_monthly")

        if plan == "pro_yearly":
            expiry = datetime.utcnow() + timedelta(days=365)
        else:
            expiry = datetime.utcnow() + timedelta(days=30)

        db.collection("users").document(uid).set({
            "uid": uid,
            "plan": "pro",
            "isPro": True,
            "subscription_status": "active",
            "subscription_start": datetime.utcnow().isoformat(),
            "subscription_end": expiry.isoformat()
        }, merge=True)

        return jsonify({
            "success": True,
            "expiryDate": expiry.isoformat()
        })
    except Exception as e:
        print("CREATE ERROR:", e)
        return jsonify({"error": str(e)}), 500

# 🔥 Authentication APIs (unchanged)
@app.route('/api/auth/login', methods=['POST'])
def api_login():
    try:
        data = request.get_json()
        email = data.get('email')
        uid = email.split('@')[0]

        resp = jsonify({
            'success': True,
            'user': {
                'uid': uid,
                'email': email,
                'displayName': uid
            }
        })

        resp.set_cookie(
            'auth_token',
            f"demo_{uid}",
            max_age=3600*24*30
        )

        print("LOGIN:", uid)
        return resp
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/auth/logout', methods=['POST'])
@login_required
def api_logout(current_user_uid):
    resp = jsonify({'success': True})
    resp.set_cookie('auth_token', '', expires=0)
    return resp

@app.route('/api/auth/me', methods=['GET'])
@login_required
def api_current_user(current_user_uid):
    db = firestore.client()
    user_doc = db.collection('users').document(current_user_uid).get()
    
    plan = 'free'
    is_pro = False
    expiry = None
    
    if user_doc.exists:
        data = user_doc.to_dict()
        plan = data.get('plan', 'free')
        expiry = data.get('subscription_end')
        if plan == 'pro' and expiry:
            is_pro = datetime.fromisoformat(expiry) > datetime.now()
    
    return jsonify({
        'uid': current_user_uid,
        'email': f"{current_user_uid}@demo.com",
        'displayName': current_user_uid.replace('demo_', ''),
        'isPro': is_pro,
        'plan': plan
    })

# 🔥 Profile & Favorites APIs (unchanged)
@app.route('/api/profile', methods=['GET', 'POST'])
@login_required
def api_profile(current_user_uid):
    db = firestore.client()
    if request.method == 'GET':
        user_doc = db.collection('users').document(current_user_uid).get()
        if user_doc.exists:
            data = user_doc.to_dict()
            data['uid'] = current_user_uid
            return jsonify(data)
        return jsonify({'uid': current_user_uid, 'plan': 'free'})
    
    data = request.get_json()
    db.collection('users').document(current_user_uid).set(data, merge=True)
    return jsonify({'success': True})

@app.route('/api/favorites', methods=['GET', 'POST', 'DELETE'])
@login_required
def api_favorites(current_user_uid):
    db = firestore.client()
    user_ref = db.collection('users').document(current_user_uid)
    
    if request.method == 'GET':
        user_doc = user_ref.get()
        favorites = user_doc.to_dict().get('favorites', {}).get('tenders', []) if user_doc.exists else []
        return jsonify({'favorites': favorites, 'count': len(favorites)})
    
    data = request.get_json()
    tender_id = data.get('tender_id')
    user_doc = user_ref.get()
    
    favorites = user_doc.to_dict().get('favorites', {'tenders': [], 'count': 0}) if user_doc.exists else {'tenders': [], 'count': 0}
    
    if request.method == 'POST':
        if tender_id not in favorites['tenders']:
            favorites['tenders'].append(tender_id)
            favorites['count'] += 1
    elif request.method == 'DELETE' and tender_id in favorites['tenders']:
        favorites['tenders'].remove(tender_id)
        favorites['count'] -= 1
    
    user_ref.set({'favorites': favorites}, merge=True)
    return jsonify({'success': True, 'count': favorites['count']})

@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})



# 🔥 Add these routes to your existing main.py (after static routes)

# 🔥 LEGAL & STATIC PAGES
@app.route('/privacy')
def privacy():
    return send_from_directory('static', 'privacy.html')

@app.route('/terms')
@app.route('/terms-of-service')
def terms():
    return send_from_directory('static', 'terms.html')

@app.route('/refund')
def refund():
    return send_from_directory('static', 'refund.html')

@app.route('/security')
def security():
    return send_from_directory('static', 'security.html')

@app.route('/contact')
def contact():
    return send_from_directory('static', 'contact.html')

@app.route('/careers')
def careers():
    return send_from_directory('static', 'careers.html')

@app.route('/blog')
def blog():
    return send_from_directory('static', 'blog.html')





if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)
