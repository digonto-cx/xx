import os
import random
import string
import requests
from datetime import datetime, timezone, timedelta
from functools import wraps
from flask import (
    Flask, render_template, request, redirect, 
    url_for, session, flash, jsonify
)
from supabase import create_client, Client
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.exceptions import HTTPException

# ==========================================================
# Application Initialization & Setup
# ==========================================================
app = Flask(
    __name__, 
    template_folder='../templates', 
    static_folder='../static'
)
app.secret_key = os.getenv("SECRET_KEY", "microearnx_prod_secret_key_8829910")

# ==========================================================
# Vercel Path Fixer Middleware (404 এরর স্থায়ী সমাধান)
# ==========================================================
class VercelPathFixer:
    """
    Vercel Serverless রিকোয়েস্টে হেডার থেকে আসল URL পাথ পুনরুদ্ধার করে
    যাতে Flask-এর কোনো পেজেই 404 এরর না আসে।
    """
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        real_path = environ.get('HTTP_X_FORWARDED_URI') or environ.get('HTTP_X_MATCHED_PATH')
        if real_path:
            environ['PATH_INFO'] = real_path.split('?')[0]
        return self.wsgi_app(environ, start_response)

app.wsgi_app = VercelPathFixer(app.wsgi_app)

# ==========================================================
# Database Connection (Supabase)
# ==========================================================
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

def get_supabase() -> Client:
    """Supabase ক্লায়েন্ট রিটার্ন করে"""
    return create_client(SUPABASE_URL, SUPABASE_KEY)

# অ্যাডমিন সিকিউরিটি পাসওয়ার্ড
ADMIN_SECRET_PASS = os.getenv("ADMIN_KEY", "Admin@MicroEarnX_2026")

# ==========================================================
# Error Handlers (সার্ভার ক্র্যাশ রোধক)
# ==========================================================
@app.errorhandler(Exception)
def handle_global_error(e):
    # সাধারণ HTTP এরর (যেমন 404, 403, 405) স্বাভাবিকভাবে চলতে দেওয়া
    if isinstance(e, HTTPException):
        return e
    
    # ব্যাকএন্ড ক্র্যাশ হলে সেফ রিকভারি
    return render_template(
        'base.html', 
        content="সার্ভারে সাময়িক চাপ রয়েছে। অনুগ্রহ করে রিলোড দিন।"
    ), 200

# ==========================================================
# Authentication Guards (Decorators)
# ==========================================================
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("অনুগ্রহ করে প্রথমে লগইন করুন!", "danger")
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            flash("অ্যাডমিন এক্সেস প্রয়োজন!", "danger")
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# ==========================================================
# ImgBB Failover Engine (Multi-Key Support)
# ==========================================================
def upload_to_imgbb(file_bytes):
    """
    সবগুলো সক্রিয় ImgBB Key সিরিয়ালি চেষ্টা করে।
    একটি ফেইল হলে বা লিমিট শেষ হলে স্বয়ংক্রিয়ভাবে পরবর্তী কি ব্যবহার করে।
    """
    sb = get_supabase()
    keys_res = sb.table('imgbb_keys').select('*').eq('is_active', True).execute()
    keys = keys_res.data or []

    for key_row in keys:
        api_key = key_row['api_key']
        try:
            url = "https://api.imgbb.com/1/upload"
            payload = {'key': api_key}
            files = {'image': file_bytes}
            res = requests.post(url, data=payload, files=files, timeout=8)
            data = res.json()
            
            if res.status_code == 200 and data.get('success'):
                return data['data']['url']
            else:
                continue
        except Exception:
            continue
            
    return None

# ==========================================================
# TUTORIAL & GUIDELINE VIDEO CONTROLLER
# ==========================================================
@app.route('/tutorial')
def tutorial():
    # ফেসবুক রিলস ভিডিওর লিংক (প্রয়োজনে আপনি আপনার নিজস্ব রিলস লিংক দিয়ে রিপ্লেস করতে পারেন)
    fb_reel_url = "https://www.facebook.com/reel/1015849843657384/"
    return render_template('tutorial.html', fb_reel_url=fb_reel_url)
    
# ==========================================================
# User Auth & Device Security
# ==========================================================
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

# ==========================================================
# SPONSORSHIP & PARTNER PROGRAM CONTROLLER
# ==========================================================
@app.route('/sponsor', methods=['GET', 'POST'])
def sponsor():
    sb = get_supabase()
    user = None
    is_logged_in = 'user_id' in session

    if is_logged_in:
        user = sb.table('users').select('*').eq('id', session['user_id']).single().execute().data

    if request.method == 'POST':
        # শর্ত: লগইন ছাড়া স্পনসর ফর্ম সাবমিট হবে না
        if not is_logged_in:
            flash("স্পনসরশিপের জন্য আবেদন করতে অনুগ্রহ করে প্রথমে লগইন করুন!", "danger")
            return redirect(url_for('index'))

        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        link = request.form.get('link', '').strip()
        description = request.form.get('description', '').strip()

        if not name or not email or not link or not description:
            flash("সবগুলো তথ্য সঠিকভাবে পূরণ করুন!", "danger")
            return redirect(url_for('sponsor'))

        sb.table('sponsors').insert({
            'user_id': session['user_id'],
            'name': name,
            'email': email,
            'link': link,
            'description': description
        }).execute()

        flash("🎉 অভিনন্দন! আপনার স্পনসরশিপ আবেদন সফলভাবে জমা হয়েছে। আমাদের পার্টনারশিপ টিম দ্রুতই আপনার সাথে যোগাযোগ করবে।", "success")
        return redirect(url_for('sponsor'))

    return render_template('sponsor.html', is_logged_in=is_logged_in, user=user)
    
@app.route('/register', methods=['POST'])
def register():
    sb = get_supabase()
    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '')
    ref_by = request.form.get('ref_by', '').strip()
    device_id = request.form.get('device_id', '').strip()

    if not name or not email or not password or not device_id:
        flash("সবগুলো তথ্য সঠিকভাবে পূরণ করুন!", "danger")
        return redirect(url_for('index'))

    # শর্ত: ১ ডিভাইসে কেবল ১টি অ্যাকাউন্ট
    existing_device = sb.table('users').select('id').eq('device_id', device_id).execute().data
    if existing_device:
        flash("এই ডিভাইস থেকে ইতিমধ্যে একটি অ্যাকাউন্ট খোলা হয়েছে! নতুন অ্যাকাউন্ট খোলা যাবে না।", "danger")
        return redirect(url_for('index'))

    # ইমেইল চেক
    existing_email = sb.table('users').select('id').eq('email', email).execute().data
    if existing_email:
        flash("এই ইমেইল দিয়ে ইতিমধ্যে অ্যাকাউন্ট তৈরি করা আছে!", "danger")
        return redirect(url_for('index'))

    ref_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    initial_balance = 50.00  # সরাসরি সাইন-আপ বোনাস

    # রেফারেল সিস্টেম ভ্যালিডেশন
    valid_referrer = None
    if ref_by:
        referrer_res = sb.table('users').select('*').eq('referral_code', ref_by).execute().data
        if referrer_res:
            referrer = referrer_res[0]
            # একই ডিভাইসে সেলফ-রেফার ব্লক
            if referrer['device_id'] != device_id:
                valid_referrer = referrer
                initial_balance = 100.00  # রেফারে জয়েন করলে ১০০ টাকা
                # রেফারার পাবে ১৫ টাকা
                sb.table('users').update({
                    'balance': float(referrer['balance']) + 15.00
                }).eq('id', referrer['id']).execute()

    new_user = {
        'name': name,
        'email': email,
        'password_hash': generate_password_hash(password),
        'device_id': device_id,
        'referral_code': ref_code,
        'referred_by': valid_referrer['referral_code'] if valid_referrer else None,
        'balance': initial_balance
    }

    try:
        inserted = sb.table('users').insert(new_user).execute()
        if inserted.data:
            session['user_id'] = inserted.data[0]['id']
            session['user_name'] = name
            flash(f"অভিনন্দন! আপনি ৳{initial_balance:.2f} জয়েনিং বোনাস পেয়েছেন।", "success")
            return redirect(url_for('dashboard'))
    except Exception:
        flash("রেজিস্ট্রেশন ব্যর্থ হয়েছে। পরে চেষ্টা করুন।", "danger")
        
    return redirect(url_for('index'))

@app.route('/login', methods=['POST'])
def login():
    sb = get_supabase()
    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '')

    user_res = sb.table('users').select('*').eq('email', email).execute().data
    if not user_res:
        flash("ইমেইল বা পাসওয়ার্ড সঠিক নয়!", "danger")
        return redirect(url_for('index'))

    user = user_res[0]
    if user['is_banned']:
        flash("আপনার অ্যাকাউন্টটি স্থায়ীভাবে ব্যান করা হয়েছে!", "danger")
        return redirect(url_for('index'))

    if check_password_hash(user['password_hash'], password):
        session['user_id'] = user['id']
        session['user_name'] = user['name']
        return redirect(url_for('dashboard'))
    else:
        flash("ভুল পাসওয়ার্ড দিয়েছেন!", "danger")
        return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# ==========================================================
# USER ACCOUNT & PROFILE CONTROLLER
# ==========================================================
@app.route('/account', methods=['GET', 'POST'])
@login_required
def account():
    sb = get_supabase()
    user_id = session['user_id']
    user = sb.table('users').select('*').eq('id', user_id).single().execute().data

    if request.method == 'POST':
        name = request.form.get('name', '').strip() or user['name']
        fb_link = request.form.get('fb_link', '').strip()
        tg_link = request.form.get('tg_link', '').strip()
        avatar_file = request.files.get('avatar')

        update_payload = {
            'name': name,
            'fb_link': fb_link if fb_link else None,
            'tg_link': tg_link if tg_link else None
        }

        # প্রোফাইল ছবি ImgBB Failover-এ আপলোড
        if avatar_file and avatar_file.filename != '':
            img_url = upload_to_imgbb(avatar_file.read())
            if img_url:
                update_payload['avatar_url'] = img_url
            else:
                flash("ইমেজ আপলোড ফেইল হয়েছে, সার্ভার ব্যস্ত!", "danger")
                return redirect(url_for('account'))

        sb.table('users').update(update_payload).eq('id', user_id).execute()
        flash("প্রোফাইল তথ্য সফলভাবে আপডেট হয়েছে!", "success")
        return redirect(url_for('account'))

    # রেফারেল ও টাস্ক সম্পন্ন সংখ্যা
    ref_count = len(sb.table('users').select('id').eq('referred_by', user['referral_code']).execute().data or [])
    completed_tasks = len(sb.table('submissions').select('id').eq('user_id', user_id).eq('status', 'approved').execute().data or [])

    return render_template('account.html', user=user, ref_count=ref_count, completed_tasks=completed_tasks)


# ==========================================================
# REFERRAL PAGE CONTROLLER
# ==========================================================
@app.route('/refer')
@login_required
def refer_page():
    sb = get_supabase()
    user_id = session['user_id']
    user = sb.table('users').select('*').eq('id', user_id).single().execute().data

    # ইউজারের রেফারেল কোড ব্যবহার করে যারা জয়েন করেছে তাদের তালিকা
    referred_users = sb.table('users').select('name, email, created_at') \
        .eq('referred_by', user['referral_code']) \
        .order('id', desc=True).execute().data or []

    # মোট রেফারেল আয়
    total_earned = len(referred_users) * 15.00

    return render_template(
        'refer.html',
        user=user,
        referred_users=referred_users,
        total_earned=total_earned
   ) 
    
# ==========================================================
# User Portal & Earning Features
# ==========================================================
@app.route('/app')
@login_required
def dashboard():
    sb = get_supabase()
    user = sb.table('users').select('*').eq('id', session['user_id']).single().execute().data
    
    # নোটিশ লোড করা
    notice_res = sb.table('settings').select('value').eq('key', 'site_notice').execute().data
    site_notice = notice_res[0]['value'] if notice_res else ""

    # মোট রেফার সংখ্যা
    ref_count = len(sb.table('users').select('id').eq('referred_by', user['referral_code']).execute().data or [])
    
    return render_template(
        'dashboard.html', 
        user=user, 
        notice=site_notice, 
        referral_count=ref_count
    )

@app.route('/tasks')
@login_required
def tasks():
    sb = get_supabase()
    # ইউজারের পেন্ডিং ও অনুমোদিত টাস্ক তালিকা
    user_subs = sb.table('submissions').select('task_id, status').eq('user_id', session['user_id']).execute().data or []
    hidden_task_ids = [s['task_id'] for s in user_subs if s['status'] in ['pending', 'approved']]

    # অ্যাক্টিভ টাস্ক ফিল্টার
    all_tasks = sb.table('tasks').select('*').eq('is_active', True).execute().data or []
    available_tasks = [t for t in all_tasks if t['id'] not in hidden_task_ids]

    return render_template('tasks.html', tasks=available_tasks)

@app.route('/task/<int:task_id>', methods=['GET', 'POST'])
@login_required
def task_detail(task_id):
    sb = get_supabase()
    task = sb.table('tasks').select('*').eq('id', task_id).single().execute().data
    if not task:
        flash("টাস্কটি খুঁজে পাওয়া যায়নি!", "danger")
        return redirect(url_for('tasks'))

    if request.method == 'POST':
        file = request.files.get('screenshot')
        if not file or file.filename == '':
            flash("প্রমাণের স্ক্রিনশট সিলেক্ট করুন!", "danger")
            return redirect(request.url)

        # ImgBB Failover আপলোড
        img_url = upload_to_imgbb(file.read())
        if not img_url:
            flash("ইমেজ হোস্ট সার্ভার ব্যস্ত! অনুগ্রহ করে এডমিনকে জানান।", "danger")
            return redirect(request.url)

        sb.table('submissions').insert({
            'task_id': task_id,
            'user_id': session['user_id'],
            'proof_url': img_url,
            'status': 'pending'
        }).execute()

        flash("টাস্ক প্রুফ জমা হয়েছে! এডমিন রিভিউ শেষে টাকা যোগ হবে।", "success")
        return redirect(url_for('tasks'))

    return render_template('task_details.html', task=task)

@app.route('/spin', methods=['POST'])
@login_required
def spin_wheel():
    """Daily Spin Feature"""
    sb = get_supabase()
    user_id = session['user_id']
    
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0).isoformat()
    spins_today = sb.table('daily_activities').select('id').eq('user_id', user_id).eq('activity_type', 'spin').gte('created_at', today_start).execute().data

    if len(spins_today) >= 3:
        return jsonify({"success": False, "message": "আজকের স্পিন লিমিট শেষ!"})

    reward = round(random.uniform(0.50, 5.00), 2)
    user = sb.table('users').select('balance').eq('id', user_id).single().execute().data
    
    sb.table('users').update({'balance': float(user['balance']) + reward}).eq('id', user_id).execute()
    sb.table('daily_activities').insert({
        'user_id': user_id, 
        'activity_type': 'spin', 
        'reward_earned': reward
    }).execute()

    return jsonify({"success": True, "reward": reward, "new_balance": float(user['balance']) + reward})

@app.route('/scratch', methods=['POST'])
@login_required
def scratch_card():
    """Daily Scratch Card Feature"""
    sb = get_supabase()
    user_id = session['user_id']
    
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0).isoformat()
    scratch_today = sb.table('daily_activities').select('id').eq('user_id', user_id).eq('activity_type', 'scratch').gte('created_at', today_start).execute().data

    if len(scratch_today) >= 3:
        return jsonify({"success": False, "message": "আজকের স্ক্র্যাচ কার্ড লিমিট শেষ!"})

    reward = round(random.uniform(1.00, 6.00), 2)
    user = sb.table('users').select('balance').eq('id', user_id).single().execute().data

    sb.table('users').update({'balance': float(user['balance']) + reward}).eq('id', user_id).execute()
    sb.table('daily_activities').insert({
        'user_id': user_id, 
        'activity_type': 'scratch', 
        'reward_earned': reward
    }).execute()

    return jsonify({"success": True, "reward": reward, "new_balance": float(user['balance']) + reward})
    
@app.route('/withdraw', methods=['GET', 'POST'])
@login_required
def withdraw():
    sb = get_supabase()
    user_id = session['user_id']
    user = sb.table('users').select('*').eq('id', user_id).single().execute().data
    ref_count = len(sb.table('users').select('id').eq('referred_by', user['referral_code']).execute().data or [])

    # GET: ডেডিকেটেড পেজ রেন্ডার
    if request.method == 'GET':
        return render_template('withdraw.html', user=user, referral_count=ref_count)
        
    try:
        amount = float(request.form.get('amount', 0))
    except ValueError:
        amount = 0

    method = request.form.get('method', '').strip()
    account = request.form.get('account', '').strip()

    if amount < 500:
        flash("সর্বনিম্ন উইথড্রয়াল অ্যামাউন্ট ৫০০ টাকা!", "danger")
        return redirect(url_for('withdraw'))

    if float(user['balance']) < amount:
        flash("আপনার অ্যাকাউন্টে পর্যাপ্ত ব্যালেন্স নেই!", "danger")
        return redirect(url_for('withdraw'))

    if ref_count < 4:
        flash(f"উইথড্র করতে সর্বনিম্ন ৪টি রেফারেল প্রয়োজন! আপনার বর্তমান রেফারেল: {ref_count} টি।", "danger")
        return redirect(url_for('withdraw'))
        
    sb.table('users').update({'balance': float(user['balance']) - amount}).eq('id', user_id).execute()
    sb.table('withdrawals').insert({
        'user_id': user_id,
        'amount': amount,
        'method': method,
        'account_number': account,
        'status': 'pending'
    }).execute()

    flash("উইথড্রয়াল রিকোয়েস্ট সফলভাবে জমা হয়েছে!", "success")
    return redirect(url_for('dashboard'))


# ==========================================================
# USER HISTORY (TASKS & WITHDRAWALS)
# ==========================================================
@app.route('/history')
@login_required
def history():
    sb = get_supabase()
    user_id = session['user_id']
    user = sb.table('users').select('*').eq('id', user_id).single().execute().data

    # ১. টাস্ক সাবমিশন হিস্ট্রি
    task_subs = sb.table('submissions').select('*, tasks(title, amount)') \
        .eq('user_id', user_id).order('id', desc=True).execute().data or []

    # ২. উইথড্রয়াল হিস্ট্রি
    withdrawals = sb.table('withdrawals').select('*') \
        .eq('user_id', user_id).order('id', desc=True).execute().data or []

    return render_template(
        'history.html', 
        user=user, 
        task_subs=task_subs, 
        withdrawals=withdrawals
    )
    
# ==========================================================
# ADMIN CONTROLLER
# ==========================================================
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        secret = request.form.get('admin_key', '')
        if secret == ADMIN_SECRET_PASS:
            session['is_admin'] = True
            return redirect(url_for('admin_dashboard'))
        flash("ভুল অ্যাডমিন সিক্রেট কি!", "danger")
    return render_template('admin/login.html')

@app.route('/admin')
@admin_required
def admin_dashboard():
    sb = get_supabase()
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    yesterday_start = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()

    total_users = len(sb.table('users').select('id').execute().data or [])
    today_users = len(sb.table('users').select('id').gte('created_at', today_start).execute().data or [])
    yesterday_users = len(sb.table('users').select('id').gte('created_at', yesterday_start).lt('created_at', today_start).execute().data or [])
    today_submissions = len(sb.table('submissions').select('id').gte('created_at', today_start).execute().data or [])
    
    notice_res = sb.table('settings').select('value').eq('key', 'site_notice').execute().data
    current_notice = notice_res[0]['value'] if notice_res else ""

    return render_template(
        'admin/dashboard.html',
        total_users=total_users,
        today_users=today_users,
        yesterday_users=yesterday_users,
        today_submissions=today_submissions,
        notice=current_notice
    )

# ==========================================================
# GLOBAL TEMPLATE CONTEXT (হেডারে প্রোফাইল ছবি পাওয়ার জন্য)
# ==========================================================
@app.context_processor
def inject_global_user():
    if 'user_id' in session:
        sb = get_supabase()
        u = sb.table('users').select('id, name, balance, avatar_url, referral_code') \
            .eq('id', session['user_id']).single().execute().data
        return dict(current_user=u)
    return dict(current_user=None)

# ==========================================================
# ALL WORK HUB (/allwork)
# ==========================================================
@app.route('/allwork')
@login_required
def all_work():
    return render_template('allwork.html')
    
@app.route('/admin/notice', methods=['POST'])
@admin_required
def admin_update_notice():
    sb = get_supabase()
    new_notice = request.form.get('site_notice', '').strip()
    sb.table('settings').upsert({'key': 'site_notice', 'value': new_notice}).execute()
    flash("সাইট নোটিশ সফলভাবে আপডেট হয়েছে!", "success")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/users')
@admin_required
def admin_users():
    sb = get_supabase()
    page = int(request.args.get('page', 1))
    search = request.args.get('q', '').strip()
    limit = 20
    offset = (page - 1) * limit

    query = sb.table('users').select('*')
    if search:
        query = query.ilike('email', f"%{search}%")

    users_list = query.order('id', desc=True).range(offset, offset + limit - 1).execute().data or []
    return render_template('admin/users.html', users=users_list, page=page, search=search)

@app.route('/admin/user/<int:user_id>/ban', methods=['POST'])
@admin_required
def admin_toggle_ban(user_id):
    sb = get_supabase()
    user = sb.table('users').select('is_banned').eq('id', user_id).single().execute().data
    if user:
        sb.table('users').update({'is_banned': not user['is_banned']}).eq('id', user_id).execute()
        flash("ইউজার স্ট্যাটাস পরিবর্তন করা হয়েছে।", "success")
    return redirect(request.referrer or url_for('admin_users'))

@app.route('/admin/user/<int:user_id>/balance', methods=['POST'])
@admin_required
def admin_modify_balance(user_id):
    sb = get_supabase()
    try:
        amount = float(request.form.get('amount', 0))
    except ValueError:
        amount = 0
        
    user = sb.table('users').select('balance').eq('id', user_id).single().execute().data
    if user:
        new_balance = float(user['balance']) + amount
        sb.table('users').update({'balance': new_balance}).eq('id', user_id).execute()
        flash("ব্যালেন্স আপডেট সফল হয়েছে!", "success")
    return redirect(request.referrer or url_for('admin_users'))

@app.route('/admin/user/<int:user_id>/delete', methods=['POST'])
@admin_required
def admin_delete_user(user_id):
    sb = get_supabase()
    sb.table('users').delete().eq('id', user_id).execute()
    flash("ইউজার ডিলিট করা হয়েছে!", "success")
    return redirect(url_for('admin_users'))

@app.route('/admin/withdraw')
@admin_required
def admin_withdraw():
    sb = get_supabase()
    reqs = sb.table('withdrawals').select('*, users(email, balance)').eq('status', 'pending').order('id', desc=True).execute().data or []

    # ইউজারের আগের মোট রিজেকশন হিস্ট্রি গণনা
    for r in reqs:
        rej_count = len(sb.table('withdrawals').select('id').eq('user_id', r['user_id']).eq('status', 'rejected').execute().data or [])
        r['rejection_count'] = rej_count

    return render_template('admin/withdraw.html', requests=reqs)

@app.route('/admin/withdraw/<int:withdraw_id>/<action>', methods=['POST'])
@admin_required
def admin_handle_withdraw(withdraw_id, action):
    sb = get_supabase()
    req = sb.table('withdrawals').select('*').eq('id', withdraw_id).single().execute().data
    if not req or req['status'] != 'pending':
        flash("অবৈধ রিকোয়েস্ট!", "danger")
        return redirect(url_for('admin_withdraw'))

    if action == 'approve':
        sb.table('withdrawals').update({'status': 'approved'}).eq('id', withdraw_id).execute()
        flash("উইথড্রয়াল অ্যাপ্রুভ হয়েছে!", "success")
    elif action == 'reject':
        # রিজেক্ট হলে ব্যালেন্স ইউজারের একাউন্টে রিফান্ড হবে
        user = sb.table('users').select('balance').eq('id', req['user_id']).single().execute().data
        sb.table('users').update({'balance': float(user['balance']) + float(req['amount'])}).eq('id', req['user_id']).execute()
        sb.table('withdrawals').update({'status': 'rejected'}).eq('id', withdraw_id).execute()
        flash("উইথড্রয়াল রিজেক্ট করা হয়েছে এবং টাকা ফেরত দেওয়া হয়েছে।", "warning")

    return redirect(url_for('admin_withdraw'))

@app.route('/admin/imgbb', methods=['GET', 'POST'])
@admin_required
def admin_imgbb():
    sb = get_supabase()
    if request.method == 'POST':
        key = request.form.get('api_key', '').strip()
        if key:
            sb.table('imgbb_keys').insert({'api_key': key}).execute()
            flash("ImgBB Key সফলভাবে যুক্ত হয়েছে!", "success")
        return redirect(url_for('admin_imgbb'))

    keys = sb.table('imgbb_keys').select('*').order('id', desc=True).execute().data or []
    return render_template('admin/imgbb.html', keys=keys)

@app.route('/admin/imgbb/delete/<int:key_id>', methods=['POST'])
@admin_required
def admin_imgbb_delete(key_id):
    sb = get_supabase()
    sb.table('imgbb_keys').delete().eq('id', key_id).execute()
    flash("API Key ডিলিট করা হয়েছে!", "success")
    return redirect(url_for('admin_imgbb'))

@app.route('/admin/task', methods=['GET', 'POST'])
@admin_required
def admin_task():
    sb = get_supabase()
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        amount = float(request.form.get('amount', 0))
        link = request.form.get('link', '').strip()

        sb.table('tasks').insert({
            'title': title,
            'description': description,
            'amount': amount,
            'link': link
        }).execute()
        flash("নতুন টাস্ক তৈরি হয়েছে!", "success")
        return redirect(url_for('admin_task'))

    all_tasks = sb.table('tasks').select('*').order('id', desc=True).execute().data or []
    return render_template('admin/tasks.html', tasks=all_tasks)

@app.route('/admin/submit')
@admin_required
def admin_submissions():
    sb = get_supabase()
    pending = sb.table('submissions').select('*, tasks(title, amount), users(email)').eq('status', 'pending').order('id', desc=True).execute().data or []
    return render_template('admin/submissions.html', submissions=pending)

# ==========================================================
# Bulk Review Engine (Max 30, Auto 3 Reject, Rest Approve)
# ==========================================================
@app.route('/admin/submit/bulk', methods=['POST'])
@admin_required
def admin_bulk_submissions():
    sb = get_supabase()
    pending = sb.table('submissions').select('*, tasks(amount)').eq('status', 'pending').limit(30).execute().data or []
    
    if not pending:
        flash("কোনো পেন্ডিং টাস্ক নেই।", "info")
        return redirect(url_for('admin_submissions'))

    # সর্বোচ্চ ৩টি র‍্যান্ডম রিজেক্ট নির্বাচন
    reject_count = min(3, len(pending))
    rejected_items = random.sample(pending, reject_count)
    rejected_ids = [item['id'] for item in rejected_items]

    approved_count = 0
    for item in pending:
        if item['id'] in rejected_ids:
            # Reject
            sb.table('submissions').update({'status': 'rejected'}).eq('id', item['id']).execute()
        else:
            # Approve + ইউজারের ব্যালেন্সে টাকা যুক্ত করা
            sb.table('submissions').update({'status': 'approved'}).eq('id', item['id']).execute()
            user = sb.table('users').select('balance').eq('id', item['user_id']).single().execute().data
            reward = float(item['tasks']['amount']) if item.get('tasks') else 0.0
            sb.table('users').update({'balance': float(user['balance']) + reward}).eq('id', item['user_id']).execute()
            approved_count += 1

    flash(f"বাল্ক রিভিউ শেষ! {approved_count}টি অ্যাপ্রুভ এবং {reject_count}টি র‍্যান্ডমলি রিজেক্ট হয়েছে।", "success")
    return redirect(url_for('admin_submissions'))

import re

# --- YouTube Video ID Extractor Helper ---
def extract_yt_id(url):
    regex = r'(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:[^\/\n\s]+\/\S+\/|(?:v|e(?:mbed)?)\/|\S*?[?&]v=)|youtu\.be\/)([a-zA-Z0-9_-]{11})'
    match = re.search(regex, url)
    return match.group(1) if match else None

# ==========================================================
# USER YOUTUBE EARN ROUTES
# ==========================================================
@app.route('/yt')
@login_required
def yt_videos():
    sb = get_supabase()
    user_id = session['user_id']
    page = int(request.args.get('page', 1))
    limit = 20
    offset = (page - 1) * limit

    # ইউজারের ইতোমধ্যে ক্লেইম করা ভিডিওগুলো বের করা
    claimed_rows = sb.table('yt_claims').select('video_id').eq('user_id', user_id).execute().data or []
    claimed_ids = [c['video_id'] for c in claimed_rows]

    # ২০টি করে একটিভ ভিডিও আনা
    query = sb.table('yt_videos').select('*').eq('is_active', True).order('id', desc=True)
    all_videos = query.range(offset, offset + limit - 1).execute().data or []

    # ভিডিওতে ক্লেইম স্ট্যাটাস ফ্ল্যাগ বসানো
    for v in all_videos:
        v['is_claimed'] = v['id'] in claimed_ids

    total_count = len(sb.table('yt_videos').select('id').eq('is_active', True).execute().data or [])
    has_next = (offset + limit) < total_count

    return render_template('yt.html', videos=all_videos, page=page, has_next=has_next)

@app.route('/yt/claim', methods=['POST'])
@login_required
def yt_claim():
    sb = get_supabase()
    user_id = session['user_id']
    data = request.get_json() or {}
    video_id = data.get('video_id')

    if not video_id:
        return jsonify({'success': False, 'message': 'অবৈধ ভিডিও আইডি!'})

    # ১. ইউজার ইতিমধ্যে ক্লেইম করেছে কিনা চেক
    already_claimed = sb.table('yt_claims').select('id').eq('user_id', user_id).eq('video_id', video_id).execute().data
    if already_claimed:
        return jsonify({'success': False, 'message': 'আপনি এই ভিডিওটি ইতিমধ্যে ক্লেইম করেছেন!'})

    # ২. ভিডিও তথ্য যাচাই
    video = sb.table('yt_videos').select('*').eq('id', video_id).single().execute().data
    if not video or not video.get('is_active'):
        return jsonify({'success': False, 'message': 'ভিডিওটি সক্রিয় নেই!'})

    amount = float(video['amount'])

    # ৩. ইউজারের ব্যালেন্সে টাকা যোগ এবং ক্লেইম হিস্ট্রি তৈরি
    user = sb.table('users').select('balance').eq('id', user_id).single().execute().data
    new_balance = float(user['balance']) + amount

    sb.table('users').update({'balance': new_balance}).eq('id', user_id).execute()
    sb.table('yt_claims').insert({
        'video_id': video_id,
        'user_id': user_id,
        'amount_earned': amount
    }).execute()

    return jsonify({
        'success': True,
        'message': f'🎉 অভিনন্দন! আপনি ৳{amount:.2f} সফলভাবে ক্লেইম করেছেন!',
        'new_balance': new_balance
    })

# ==========================================================
# ADMIN YOUTUBE CONTROLLER
# ==========================================================
@app.route('/admin/yt', methods=['GET', 'POST'])
@admin_required
def admin_yt():
    sb = get_supabase()
    if request.method == 'POST':
        raw_url = request.form.get('video_url', '').strip()
        title = request.form.get('title', '').strip() or 'YouTube Video'
        try:
            amount = float(request.form.get('amount', 1.00))
        except ValueError:
            amount = 1.00

        vid = extract_yt_id(raw_url)
        if not vid:
            flash("ইউটিউব লিংক সঠিক নয়! (যেমন: https://youtu.be/... বা watch?v=... দিন)", "danger")
            return redirect(url_for('admin_yt'))

        sb.table('yt_videos').insert({
            'video_url': raw_url,
            'video_id': vid,
            'title': title,
            'amount': amount
        }).execute()

        flash("নতুন YouTube ভিডিও সফলভাবে যুক্ত হয়েছে!", "success")
        return redirect(url_for('admin_yt'))

    videos = sb.table('yt_videos').select('*').order('id', desc=True).execute().data or []
    return render_template('admin/yt.html', videos=videos)

@app.route('/admin/yt/delete/<int:video_id>', methods=['POST'])
@admin_required
def admin_yt_delete(video_id):
    sb = get_supabase()
    sb.table('yt_videos').delete().eq('id', video_id).execute()
    flash("ভিডিওটি সফলভাবে ডিলিট করা হয়েছে!", "success")
    return redirect(url_for('admin_yt'))

# ==========================================================
# DEDICATED SPIN & SCRATCH ROUTES
# ==========================================================
@app.route('/spin', methods=['GET', 'POST'])
@login_required
def spin_page():
    sb = get_supabase()
    user_id = session['user_id']
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0).isoformat()
    spins_today = sb.table('daily_activities').select('id').eq('user_id', user_id).eq('activity_type', 'spin').gte('created_at', today_start).execute().data or []

    # POST: স্পিন রিওয়ার্ড ক্যালকুলেশন
    if request.method == 'POST':
        if len(spins_today) >= 3:
            return jsonify({"success": False, "message": "আজকের ৩টি স্পিন লিমিট শেষ! আগামীকাল আবার আসুন।"})

        reward = round(random.uniform(0.50, 5.00), 2)
        user = sb.table('users').select('balance').eq('id', user_id).single().execute().data
        new_bal = float(user['balance']) + reward

        sb.table('users').update({'balance': new_bal}).eq('id', user_id).execute()
        sb.table('daily_activities').insert({
            'user_id': user_id, 
            'activity_type': 'spin', 
            'reward_earned': reward
        }).execute()

        remaining = max(0, 3 - (len(spins_today) + 1))
        return jsonify({"success": True, "reward": reward, "new_balance": new_bal, "remaining": remaining})

    # GET: স্পিন পেজ রেন্ডার
    user = sb.table('users').select('*').eq('id', user_id).single().execute().data
    remaining_spins = max(0, 3 - len(spins_today))
    return render_template('spin.html', user=user, remaining=remaining_spins)

@app.route('/scratch', methods=['GET', 'POST'])
@login_required
def scratch_page():
    sb = get_supabase()
    user_id = session['user_id']
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0).isoformat()
    scratch_today = sb.table('daily_activities').select('id').eq('user_id', user_id).eq('activity_type', 'scratch').gte('created_at', today_start).execute().data or []

    # POST: স্ক্র্যাচ রিওয়ার্ড ক্যালকুলেশন
    if request.method == 'POST':
        if len(scratch_today) >= 3:
            return jsonify({"success": False, "message": "আজকের ৩টি স্ক্র্যাচ লিমিট শেষ! আগামীকাল আবার আসুন।"})

        reward = round(random.uniform(1.00, 6.00), 2)
        user = sb.table('users').select('balance').eq('id', user_id).single().execute().data
        new_bal = float(user['balance']) + reward

        sb.table('users').update({'balance': new_bal}).eq('id', user_id).execute()
        sb.table('daily_activities').insert({
            'user_id': user_id, 
            'activity_type': 'scratch', 
            'reward_earned': reward
        }).execute()

        remaining = max(0, 3 - (len(scratch_today) + 1))
        return jsonify({"success": True, "reward": reward, "new_balance": new_bal, "remaining": remaining})

    # GET: স্ক্র্যাচ পেজ রেন্ডার
    user = sb.table('users').select('*').eq('id', user_id).single().execute().data
    remaining_scratch = max(0, 3 - len(scratch_today))
    return render_template('scratch.html', user=user, remaining=remaining_scratch)


# ==========================================================
# ADVERTISER & PROMOTION LANDING CONTROLLER
# ==========================================================
@app.route('/promote', methods=['GET', 'POST'])
def promote():
    sb = get_supabase()
    user = None
    is_logged_in = 'user_id' in session

    if is_logged_in:
        user = sb.table('users').select('*').eq('id', session['user_id']).single().execute().data

    if request.method == 'POST':
        # শর্ত: লগইন ছাড়া ফর্ম সাবমিট হবে না
        if not is_logged_in:
            flash("প্রমোশন ফর্ম জমা দিতে অনুগ্রহ করে প্রথমে লগইন করুন!", "danger")
            return redirect(url_for('index'))

        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        service_type = request.form.get('service_type', 'General').strip()
        requirement = request.form.get('requirement', '').strip()

        if not name or not email or not phone or not requirement:
            flash("ফর্মের সবকটি তথ্য সঠিকভাবে পূরণ করুন!", "danger")
            return redirect(url_for('promote'))

        sb.table('promotions').insert({
            'user_id': session['user_id'],
            'name': name,
            'email': email,
            'phone': phone,
            'service_type': service_type,
            'requirement': requirement
        }).execute()

        flash("🎉 আপনার রিকোয়েস্ট সফলভাবে জমা হয়েছে! আমাদের টিম দ্রুতই আপনার সাথে যোগাযোগ করবে।", "success")
        return redirect(url_for('promote'))

    return render_template('promote.html', is_logged_in=is_logged_in, user=user)
    
# ==========================================================
# Local Development Execution
# ==========================================================
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
