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

# ==========================================================
# Application Configuration
# ==========================================================
app = Flask(
    __name__, 
    template_folder='../templates', 
    static_folder='../static'
)
app.secret_key = os.getenv("SECRET_KEY", "microearnx_prod_secret_key_8829910")

# Supabase Initialization
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

def get_supabase() -> Client:
    """Creates a connection instance with Supabase."""
    return create_client(SUPABASE_URL, SUPABASE_KEY)

# Admin Security Key
ADMIN_SECRET_PASS = os.getenv("ADMIN_KEY", "Admin@MicroEarnX_2026")

# ==========================================================
# High-Traffic & 500 Crash Handlers
# ==========================================================
@app.errorhandler(500)
def server_error_handler(e):
    return render_template(
        'base.html', 
        content="সার্ভারে অতিরিক্ত লোড রয়েছে। অনুগ্রহ করে ১ মিনিট পর আবার চেষ্টা করুন।"
    ), 200

@app.errorhandler(Exception)
def global_exception_handler(e):
    # Serverless disconnect hole crash na kore clean JSON/Redirect dibe
    if request.path.startswith('/api/'):
        return jsonify({"success": False, "message": "System busy, try again.", "error": str(e)}), 200
    flash("নেটওয়ার্ক সমস্যা হয়েছে, অনুগ্রহ করে পুনরায় চেষ্টা করুন।", "warning")
    return redirect(url_for('index'))

# ==========================================================
# Auth Decorators
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
            flash("শুধুমাত্র অ্যাডমিন এক্সেস অনুমোদিত!", "danger")
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# ==========================================================
# ImgBB Failover Engine (Multi-Key Dynamic Fallback)
# ==========================================================
def upload_to_imgbb(file_bytes):
    """
    Loop kore shob active ImgBB key check korbe।
    Akta key fail hole auto porer key diye try korbe।
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
                # Key er limit sesh ba error, porer key try korbe
                continue
        except Exception:
            continue
            
    return None

# ==========================================================
# Authentication & Device Protection
# ==========================================================
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

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

    # ১ ডিভাইসে ১ অ্যাকাউন্ট কঠোর চেকিং
    existing_device = sb.table('users').select('id').eq('device_id', device_id).execute().data
    if existing_device:
        flash("এই ডিভাইস থেকে ইতিমধ্যে একটি অ্যাকাউন্ট খোলা হয়েছে! নতুন অ্যাকাউন্ট খোলা সম্ভব নয়।", "danger")
        return redirect(url_for('index'))

    # ইমেইল ডুপ্লিকেট চেকিং
    existing_email = sb.table('users').select('id').eq('email', email).execute().data
    if existing_email:
        flash("এই ইমেইল দিয়ে ইতিমধ্যে অ্যাকাউন্ট রয়েছে!", "danger")
        return redirect(url_for('index'))

    # রেফারেল কোড জেনারেশন (৬ ক্যারেক্টার)
    ref_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    initial_balance = 50.00  # নরমাল সাইন-আপ বোনাস

    # রেফারেল সিস্টেম ভ্যালিডেশন
    valid_referrer = None
    if ref_by:
        referrer_res = sb.table('users').select('*').eq('referral_code', ref_by).execute().data
        if referrer_res:
            referrer = referrer_res[0]
            # সেইম ডিভাইসে সেলফ-রেফারেল ব্লক
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
    except Exception as e:
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
# User Portal & Earning Features
# ==========================================================
@app.route('/app')
@login_required
def dashboard():
    sb = get_supabase()
    user = sb.table('users').select('*').eq('id', session['user_id']).single().execute().data
    
    # নোটিশ আনা
    notice_res = sb.table('settings').select('value').eq('key', 'site_notice').execute().data
    site_notice = notice_res[0]['value'] if notice_res else "MicroEarnX এ আপনাকে স্বাগতম!"

    # মোট রেফারেল সংখ্যা গণনা
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
    # ইউজারের পেন্ডিং ও অ্যাপ্রুভড টাস্ক বের করা
    user_subs = sb.table('submissions').select('task_id, status').eq('user_id', session['user_id']).execute().data or []
    hidden_task_ids = [s['task_id'] for s in user_subs if s['status'] in ['pending', 'approved']]

    # শুধু একটিভ এবং পেন্ডিং/অ্যাপ্রুভড ছাড়া বাকি টাস্ক আনা
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

        # ImgBB Failover Upload
        img_url = upload_to_imgbb(file.read())
        if not img_url:
            flash("ইমেজ সার্ভার ব্যস্ত! এডমিনের সাথে যোগাযোগ করুন।", "danger")
            return redirect(request.url)

        sb.table('submissions').insert({
            'task_id': task_id,
            'user_id': session['user_id'],
            'proof_url': img_url,
            'status': 'pending'
        }).execute()

        flash("টাস্ক প্রুফ সফলভাবে জমা হয়েছে! এডমিন রিভিউ করবে।", "success")
        return redirect(url_for('tasks'))

    return render_template('task_details.html', task=task)

@app.route('/spin', methods=['POST'])
@login_required
def spin_wheel():
    """Daily Spin Feature"""
    sb = get_supabase()
    user_id = session['user_id']
    
    # আজকের ডেট
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

# ==========================================================
# Withdrawal System (With Rejection Count & Validation)
# ==========================================================
@app.route('/withdraw', methods=['POST'])
@login_required
def withdraw():
    sb = get_supabase()
    user_id = session['user_id']
    user = sb.table('users').select('*').eq('id', user_id).single().execute().data
    
    try:
        amount = float(request.form.get('amount', 0))
    except ValueError:
        amount = 0

    method = request.form.get('method', '').strip()
    account = request.form.get('account', '').strip()

    # শর্ত ১: মিনিমাম উইথড্রয়াল ৫০০ টাকা
    if amount < 500:
        flash("সর্বনিম্ন উইথড্রয়াল অ্যামাউন্ট ৫০০ টাকা!", "danger")
        return redirect(url_for('dashboard'))

    if float(user['balance']) < amount:
        flash("আপনার অ্যাকাউন্টে পর্যাপ্ত ব্যালেন্স নেই!", "danger")
        return redirect(url_for('dashboard'))

    # শর্ত ২: কমপক্ষে ৪টি সফল রেফারেল থাকতে হবে
    ref_count = len(sb.table('users').select('id').eq('referred_by', user['referral_code']).execute().data or [])
    if ref_count < 4:
        flash(f"উইথড্র করতে সর্বনিম্ন ৪টি রেফারেল আবশ্যক! আপনার বর্তমান রেফার: {ref_count} টি।", "danger")
        return redirect(url_for('dashboard'))

    # ব্যালেন্স কেটে পেন্ডিং উইথড্রয়াল ইনসার্ট করা
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
    amount = float(request.form.get('amount', 0))
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
    flash("ইউজার সফলভাবে ডিলিট করা হয়েছে!", "success")
    return redirect(url_for('admin_users'))

@app.route('/admin/withdraw')
@admin_required
def admin_withdraw():
    sb = get_supabase()
    # পেন্ডিং উইথড্রয়াল গুলো আনা
    reqs = sb.table('withdrawals').select('*, users(email, balance)').eq('status', 'pending').order('id', desc=True).execute().data or []

    # প্রত্যেক ইউজারের আগের রিজেকশন কাউন্ট বের করা
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
        flash("ইনভ্যালিড রিকোয়েস্ট!", "danger")
        return redirect(url_for('admin_withdraw'))

    if action == 'approve':
        sb.table('withdrawals').update({'status': 'approved'}).eq('id', withdraw_id).execute()
        flash("উইথড্রয়াল অ্যাপ্রুভ করা হয়েছে!", "success")
    elif action == 'reject':
        # রিজেক্ট হলে ব্যালেন্স ব্যাক দেওয়া হবে
        user = sb.table('users').select('balance').eq('id', req['user_id']).single().execute().data
        sb.table('users').update({'balance': float(user['balance']) + float(req['amount'])}).eq('id', req['user_id']).execute()
        sb.table('withdrawals').update({'status': 'rejected'}).eq('id', withdraw_id).execute()
        flash("উইথড্রয়াল রিজেক্ট করা হয়েছে এবং ব্যালেন্স ফেরত দেওয়া হয়েছে।", "warning")

    return redirect(url_for('admin_withdraw'))

@app.route('/admin/imgbb', methods=['GET', 'POST'])
@admin_required
def admin_imgbb():
    sb = get_supabase()
    if request.method == 'POST':
        key = request.form.get('api_key', '').strip()
        if key:
            sb.table('imgbb_keys').insert({'api_key': key}).execute()
            flash("নতুন ImgBB API Key যুক্ত হয়েছে!", "success")
        return redirect(url_for('admin_imgbb'))

    keys = sb.table('imgbb_keys').select('*').order('id', desc=True).execute().data or []
    return render_template('admin/imgbb.html', keys=keys)

@app.route('/admin/imgbb/delete/<int:key_id>', methods=['POST'])
@admin_required
def admin_imgbb_delete(key_id):
    sb = get_supabase()
    sb.table('imgbb_keys').delete().eq('id', key_id).execute()
    flash("API Key মুছে ফেলা হয়েছে!", "success")
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
        flash("নতুন টাস্ক সফলভাবে তৈরি হয়েছে!", "success")
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
    # সর্বোচ্চ ৩০টি পেন্ডিং টাস্ক নেওয়া
    pending = sb.table('submissions').select('*, tasks(amount)').eq('status', 'pending').limit(30).execute().data or []
    
    if not pending:
        flash("রিভিউ করার জন্য কোনো পেন্ডিং টাস্ক নেই।", "info")
        return redirect(url_for('admin_submissions'))

    # র‍্যান্ডম ৩টি রিজেক্ট সিলেক্ট করা
    reject_count = min(3, len(pending))
    rejected_items = random.sample(pending, reject_count)
    rejected_ids = [item['id'] for item in rejected_items]

    approved_count = 0
    for item in pending:
        if item['id'] in rejected_ids:
            # Reject
            sb.table('submissions').update({'status': 'rejected'}).eq('id', item['id']).execute()
        else:
            # Approve + ব্যালেন্স অ্যাড
            sb.table('submissions').update({'status': 'approved'}).eq('id', item['id']).execute()
            user = sb.table('users').select('balance').eq('id', item['user_id']).single().execute().data
            reward = float(item['tasks']['amount']) if item.get('tasks') else 0.0
            sb.table('users').update({'balance': float(user['balance']) + reward}).eq('id', item['user_id']).execute()
            approved_count += 1

    flash(f"বাল্ক সম্পন্ন! {approved_count}টি অ্যাপ্রুভ করা হয়েছে এবং {reject_count}টি র‍্যান্ডমলি রিজেক্ট হয়েছে।", "success")
    return redirect(url_for('admin_submissions'))

# ==========================================================
# Run Locally (Only if not hosted on Vercel)
# ==========================================================
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
