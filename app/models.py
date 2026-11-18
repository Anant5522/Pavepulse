from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app.database import db

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='citizen') # 'citizen', 'officer', 'admin'
    phone = db.Column(db.String(20), nullable=True)
    karma_points = db.Column(db.Integer, default=150)
    badge = db.Column(db.String(50), default='🥉 Civic Scout')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    reports = db.relationship('Report', backref='reporter', lazy=True, foreign_keys='Report.user_id')
    assigned_tasks = db.relationship('Assignment', backref='officer', lazy=True, foreign_keys='Assignment.officer_id')
    maintenance_records = db.relationship('Maintenance', backref='officer', lazy=True, foreign_keys='Maintenance.officer_id')
    notifications = db.relationship('Notification', backref='user', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == 'admin'

    @property
    def is_officer(self):
        return self.role == 'officer'

    @property
    def is_citizen(self):
        return self.role == 'citizen'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'role': self.role,
            'phone': self.phone,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Hazard(db.Model):
    __tablename__ = 'hazards'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(50), nullable=False, index=True) # pothole, damaged_road, waterlogging, etc.
    description = db.Column(db.Text, nullable=True)
    default_severity = db.Column(db.String(20), default='Medium') # Low, Medium, High, Critical
    base_severity_score = db.Column(db.Integer, default=20) # 0 - 40 points
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    reports = db.relationship('Report', backref='hazard_category', lazy=True)


class Report(db.Model):
    __tablename__ = 'reports'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    hazard_id = db.Column(db.Integer, db.ForeignKey('hazards.id'), nullable=True)
    
    title = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), nullable=False, index=True)
    description = db.Column(db.Text, nullable=False)
    
    latitude = db.Column(db.Float, nullable=False, index=True)
    longitude = db.Column(db.Float, nullable=False, index=True)
    address = db.Column(db.String(255), nullable=True)
    
    image_url = db.Column(db.String(500), nullable=True)
    image_key = db.Column(db.String(255), nullable=True)
    
    # Status: 'Submitted', 'Under Review', 'Assigned', 'In Progress', 'Resolved', 'Rejected', 'Reopened'
    status = db.Column(db.String(30), default='Submitted', nullable=False, index=True)
    
    # Duplicate tracking
    is_duplicate_of = db.Column(db.Integer, db.ForeignKey('reports.id'), nullable=True)
    recurrence_count = db.Column(db.Integer, default=1, nullable=False)
    
    # Road characteristics for risk scoring
    road_type = db.Column(db.String(50), default='arterial') # highway, arterial, residential, school_zone
    traffic_density = db.Column(db.String(30), default='moderate') # high, moderate, low
    accident_risk = db.Column(db.String(30), default='moderate') # high, moderate, low
    
    # Community & AI Vision Analytics
    upvotes_count = db.Column(db.Integer, default=0)
    ai_confidence = db.Column(db.Float, default=94.5)
    ai_detected_label = db.Column(db.String(100), default='Pothole / Road Depression')
    ai_severity = db.Column(db.String(20), default='Critical')
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    duplicates = db.relationship('Report', backref=db.backref('parent_report', remote_side=[id]), lazy=True)
    risk_score = db.relationship('RiskScore', backref='report', uselist=False, cascade='all, delete-orphan', lazy=True)
    assignment = db.relationship('Assignment', backref='report', uselist=False, cascade='all, delete-orphan', lazy=True)
    maintenance_records = db.relationship('Maintenance', backref='report', lazy=True, cascade='all, delete-orphan')
    status_history = db.relationship('StatusHistory', backref='report', lazy=True, cascade='all, delete-orphan', order_by='StatusHistory.changed_at.desc()')

    def to_dict(self):
        score_val = self.risk_score.total_score if self.risk_score else 0
        level_val = self.risk_score.risk_level if self.risk_score else 'Low'
        assigned_officer_name = self.assignment.officer.name if self.assignment and self.assignment.officer else None

        return {
            'id': self.id,
            'title': self.title,
            'category': self.category,
            'description': self.description,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'address': self.address,
            'image_url': self.image_url,
            'status': self.status,
            'is_duplicate': bool(self.is_duplicate_of),
            'parent_report_id': self.is_duplicate_of,
            'recurrence_count': self.recurrence_count,
            'upvotes_count': self.upvotes_count or 0,
            'ai_confidence': self.ai_confidence or 92.0,
            'ai_detected_label': self.ai_detected_label or 'Road Hazard',
            'ai_severity': self.ai_severity or 'High',
            'risk_score': score_val,
            'risk_level': level_val,
            'assigned_officer': assigned_officer_name,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else None,
            'reporter_name': self.reporter.name if self.reporter else 'Anonymous'
        }


class RiskScore(db.Model):
    __tablename__ = 'risk_scores'
    
    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey('reports.id'), nullable=False, unique=True, index=True)
    
    severity_score = db.Column(db.Integer, default=0)         # Max 40
    location_impact_score = db.Column(db.Integer, default=0)  # Max 20
    safety_impact_score = db.Column(db.Integer, default=0)    # Max 25
    recurrence_score = db.Column(db.Integer, default=0)       # Max 15
    
    total_score = db.Column(db.Integer, default=0, index=True) # Max 100
    risk_level = db.Column(db.String(20), default='Low')      # Low, Medium, High, Critical
    calculated_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'total_score': self.total_score,
            'risk_level': self.risk_level,
            'breakdown': {
                'severity': self.severity_score,
                'location': self.location_impact_score,
                'safety': self.safety_impact_score,
                'recurrence': self.recurrence_score
            }
        }


class Assignment(db.Model):
    __tablename__ = 'assignments'
    
    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey('reports.id'), nullable=False, index=True)
    officer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    assigned_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Maintenance(db.Model):
    __tablename__ = 'maintenance'
    
    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey('reports.id'), nullable=False, index=True)
    officer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    remarks = db.Column(db.Text, nullable=False)
    before_image_url = db.Column(db.String(500), nullable=True)
    after_image_url = db.Column(db.String(500), nullable=True)
    after_image_key = db.Column(db.String(255), nullable=True)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    report_id = db.Column(db.Integer, db.ForeignKey('reports.id'), nullable=True)
    message = db.Column(db.String(255), nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class StatusHistory(db.Model):
    __tablename__ = 'status_history'
    
    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey('reports.id'), nullable=False, index=True)
    old_status = db.Column(db.String(30), nullable=True)
    new_status = db.Column(db.String(30), nullable=False)
    changed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    remarks = db.Column(db.String(255), nullable=True)
    changed_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', foreign_keys=[changed_by])


class Upvote(db.Model):
    __tablename__ = 'upvotes'

    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey('reports.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('upvotes', lazy=True))
    report = db.relationship('Report', backref=db.backref('upvotes_rel', lazy=True, cascade='all, delete-orphan'))

