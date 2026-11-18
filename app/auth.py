from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from app.models import User
from app.database import db

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = "Please log in to access this page."
login_manager.login_message_category = "info"

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def role_required(*allowed_roles):
    """
    Decorator to restrict route access to specific user roles.
    Example: @role_required('admin') or @role_required('officer', 'admin')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return login_manager.unauthorized()
            if current_user.role not in allowed_roles:
                flash("Access denied: You do not have permission to view this resource.", "danger")
                return redirect(url_for('routes.index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('routes.dashboard_redirect'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        phone = request.form.get('phone', '').strip()
        role = request.form.get('role', 'citizen')

        # Limit self-registration roles for security
        if role not in ['citizen', 'officer']:
            role = 'citizen'

        if not name or not email or not password:
            flash("All required fields must be filled.", "danger")
            return render_template('auth/register.html', name=name, email=email, phone=phone, role=role)

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template('auth/register.html', name=name, email=email, phone=phone, role=role)

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return render_template('auth/register.html', name=name, email=email, phone=phone, role=role)

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("An account with this email address already exists.", "warning")
            return render_template('auth/register.html', name=name, phone=phone, role=role)

        new_user = User(
            name=name,
            email=email,
            phone=phone,
            role=role
        )
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)
        flash(f"Welcome to PavePulse, {new_user.name}! Account created successfully.", "success")
        return redirect(url_for('routes.dashboard_redirect'))

    return render_template('auth/register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('routes.dashboard_redirect'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))

        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            flash("Invalid email or password. Please try again.", "danger")
            return render_template('auth/login.html', email=email)

        login_user(user, remember=remember)
        flash(f"Signed in as {user.name} ({user.role.title()}).", "success")

        next_page = request.args.get('next')
        if next_page and next_page.startswith('/'):
            return redirect(next_page)
        return redirect(url_for('routes.dashboard_redirect'))

    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash("You have been securely signed out.", "info")
    return redirect(url_for('routes.index'))
