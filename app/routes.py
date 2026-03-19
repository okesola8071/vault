from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, limiter
from app.models import User, Wallet, Transaction, WithdrawalRequest, Rate
from app.tatum import generate_wallet, generate_address

auth = Blueprint('auth', __name__)
user = Blueprint('user', __name__)
admin = Blueprint('admin', __name__)

# ─── AUTH ROUTES ───────────────────────────────────────

@auth.route('/')
def home():
    return redirect(url_for('auth.login'))

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()

        if not full_name or not phone or not email or not password:
            flash('All fields are required', 'danger')
            return redirect(url_for('auth.register'))

        if len(password) < 8:
            flash('Password must be at least 8 characters', 'danger')
            return redirect(url_for('auth.register'))

        if len(phone) < 10:
            flash('Enter a valid phone number', 'danger')
            return redirect(url_for('auth.register'))

        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return redirect(url_for('auth.register'))

        if User.query.filter_by(phone=phone).first():
            flash('Phone number already registered', 'danger')
            return redirect(url_for('auth.register'))

        new_user = User(
            full_name=full_name,
            phone=phone,
            email=email,
            password_hash=generate_password_hash(password)
        )
        db.session.add(new_user)
        db.session.commit()

        for crypto in ['BTC', 'ETH', 'USDT']:
            wallet_data = generate_wallet(crypto)
            if wallet_data:
                address = generate_address(crypto, wallet_data['xpub'], new_user.id)
                wallet = Wallet(
                    user_id=new_user.id,
                    crypto_type=crypto,
                    wallet_address=address
                )
                db.session.add(wallet)
        db.session.commit()

        flash('Account created successfully! Please login.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html')


@auth.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()

        if not email or not password:
            flash('Please fill in all fields', 'danger')
            return redirect(url_for('auth.login'))

        user_obj = User.query.filter_by(email=email).first()

        if user_obj and check_password_hash(user_obj.password_hash, password):
            login_user(user_obj, remember=True)
            next_page = request.args.get('next')
            if user_obj.is_admin:
                return redirect(url_for('admin.dashboard'))
            return redirect(next_page or url_for('user.dashboard'))
        else:
            flash('Invalid email or password', 'danger')

    return render_template('auth/login.html')


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))


# ─── USER ROUTES ───────────────────────────────────────

@user.route('/dashboard')
@login_required
def dashboard():
    wallets = Wallet.query.filter_by(user_id=current_user.id).all()
    transactions = Transaction.query.filter_by(user_id=current_user.id).all()
    rates = Rate.query.all()
    return render_template('user/dashboard.html',
                           wallets=wallets,
                           transactions=transactions,
                           rates=rates)


@user.route('/withdraw', methods=['GET', 'POST'])
@login_required
def withdraw():
    if request.method == 'POST':
        crypto_type = request.form.get('crypto_type', '').strip()
        bank_name = request.form.get('bank_name', '').strip()
        account_number = request.form.get('account_number', '').strip()
        account_name = request.form.get('account_name', '').strip()

        if not crypto_type or not bank_name or not account_number or not account_name:
            flash('All fields are required', 'danger')
            return redirect(url_for('user.withdraw'))

        if not account_number.isdigit() or len(account_number) != 10:
            flash('Account number must be exactly 10 digits', 'danger')
            return redirect(url_for('user.withdraw'))

        try:
            crypto_amount = float(request.form.get('crypto_amount', 0))
            if crypto_amount <= 0:
                flash('Amount must be greater than 0', 'danger')
                return redirect(url_for('user.withdraw'))
        except ValueError:
            flash('Invalid amount entered', 'danger')
            return redirect(url_for('user.withdraw'))

        wallet = Wallet.query.filter_by(
            user_id=current_user.id,
            crypto_type=crypto_type
        ).first()

        if not wallet or wallet.balance < crypto_amount:
            flash('Insufficient balance', 'danger')
            return redirect(url_for('user.withdraw'))

        rate = Rate.query.filter_by(crypto_type=crypto_type).first()
        if not rate:
            flash('Rate not set for this crypto. Contact admin.', 'danger')
            return redirect(url_for('user.withdraw'))

        naira_equivalent = crypto_amount * rate.naira_rate

        withdrawal = WithdrawalRequest(
            user_id=current_user.id,
            crypto_amount=crypto_amount,
            naira_equivalent=naira_equivalent,
            bank_name=bank_name,
            account_number=account_number,
            account_name=account_name
        )
        db.session.add(withdrawal)
        db.session.commit()

        flash('Withdrawal request submitted successfully!', 'success')
        return redirect(url_for('user.dashboard'))

    wallets = Wallet.query.filter_by(user_id=current_user.id).all()
    return render_template('user/withdraw.html', wallets=wallets)


# ─── ADMIN ROUTES ───────────────────────────────────────

@admin.route('/')
@login_required
def dashboard():
    if not current_user.is_admin:
        return redirect(url_for('user.dashboard'))
    users = User.query.all()
    withdrawals = WithdrawalRequest.query.filter_by(status='pending').all()
    rates = Rate.query.all()
    return render_template('admin/dashboard.html',
                           users=users,
                           withdrawals=withdrawals,
                           rates=rates)


@admin.route('/set-rate', methods=['POST'])
@login_required
def set_rate():
    if not current_user.is_admin:
        return redirect(url_for('user.dashboard'))

    crypto_type = request.form.get('crypto_type', '').strip()
    try:
        naira_rate = float(request.form.get('naira_rate', 0))
        if naira_rate <= 0:
            flash('Rate must be greater than 0', 'danger')
            return redirect(url_for('admin.dashboard'))
    except ValueError:
        flash('Invalid rate entered', 'danger')
        return redirect(url_for('admin.dashboard'))

    rate = Rate.query.filter_by(crypto_type=crypto_type).first()
    if rate:
        rate.naira_rate = naira_rate
    else:
        rate = Rate(crypto_type=crypto_type, naira_rate=naira_rate)
        db.session.add(rate)
    db.session.commit()

    flash(f'{crypto_type} rate updated to ₦{naira_rate:,.0f}!', 'success')
    return redirect(url_for('admin.dashboard'))


@admin.route('/confirm-payment/<int:withdrawal_id>')
@login_required
def confirm_payment(withdrawal_id):
    if not current_user.is_admin:
        return redirect(url_for('user.dashboard'))
    withdrawal = WithdrawalRequest.query.get(withdrawal_id)
    if not withdrawal:
        flash('Withdrawal not found', 'danger')
        return redirect(url_for('admin.dashboard'))
    withdrawal.status = 'paid'
    db.session.commit()
    flash('Payment confirmed successfully!', 'success')
    return redirect(url_for('admin.dashboard'))

    # ─── WEBHOOK ───────────────────────────────────────

@auth.route('/webhook/tatum', methods=['POST'])
def tatum_webhook():
    data = request.get_json()

    if not data:
        return {'status': 'no data'}, 400

    try:
        # Get the wallet address that received crypto
        address = data.get('address')
        amount = float(data.get('amount', 0))
        asset = data.get('asset', '').upper()

        # Map asset names
        asset_map = {
            'BTC': 'BTC',
            'ETH': 'ETH',
            'USDT': 'USDT',
            'TETHER': 'USDT'
        }
        crypto_type = asset_map.get(asset, asset)

        # Find the wallet
        wallet = Wallet.query.filter_by(wallet_address=address).first()
        if not wallet:
            return {'status': 'wallet not found'}, 404

        # Update balance
        wallet.balance += amount

        # Record transaction
        rate = Rate.query.filter_by(crypto_type=crypto_type).first()
        naira_amount = wallet.balance * rate.naira_rate if rate else 0

        transaction = Transaction(
            user_id=wallet.user_id,
            type='deposit',
            crypto_type=crypto_type,
            crypto_amount=amount,
            naira_amount=naira_amount,
            rate_at_time=rate.naira_rate if rate else 0,
            status='completed'
        )
        db.session.add(transaction)
        db.session.commit()

        return {'status': 'success'}, 200

    except Exception as e:
        print(f"Webhook error: {e}")
        return {'status': 'error'}, 500