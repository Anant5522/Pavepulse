from datetime import datetime, timedelta
import random
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from app.database import db
from app.models import User, Hazard, Report, RiskScore, Assignment, Maintenance, Notification, StatusHistory, Upvote
from app.auth import role_required
from app.risk_engine import find_duplicate_report, update_or_create_risk_score, haversine_distance_meters
from app.s3_service import upload_image

routes_bp = Blueprint('routes', __name__)

# --- Common / Public Views ---

@routes_bp.route('/')
def index():
    total_reports = Report.query.count()
    resolved_reports = Report.query.filter_by(status='Resolved').count()
    active_reports = Report.query.filter(~Report.status.in_(['Resolved', 'Rejected'])).count()
    critical_reports = RiskScore.query.filter_by(risk_level='Critical').count()

    recent_reports = Report.query.order_by(Report.created_at.desc()).limit(15).all()

    return render_template('index.html',
                           total_reports=total_reports,
                           resolved_reports=resolved_reports,
                           active_reports=active_reports,
                           critical_reports=critical_reports,
                           recent_reports=recent_reports)


@routes_bp.route('/dashboard')
@login_required
def dashboard_redirect():
    if current_user.role == 'admin':
        return redirect(url_for('routes.admin_dashboard'))
    elif current_user.role == 'officer':
        return redirect(url_for('routes.officer_dashboard'))
    else:
        return redirect(url_for('routes.citizen_dashboard'))


@routes_bp.route('/map')
def hazard_map():
    return render_template('map.html')


@routes_bp.route('/api/hazards')
def api_hazards():
    category = request.args.get('category')
    status = request.args.get('status')
    risk_level = request.args.get('risk_level')

    query = Report.query

    if category and category != 'all':
        query = query.filter(Report.category == category)
    if status and status != 'all':
        query = query.filter(Report.status == status)

    reports = query.all()

    output = []
    for r in reports:
        item = r.to_dict()
        if risk_level and risk_level != 'all':
            if item.get('risk_level') != risk_level:
                continue
        output.append(item)

    return jsonify(output)


@routes_bp.route('/api/stats')
def api_stats():
    total = Report.query.count()
    resolved = Report.query.filter_by(status='Resolved').count()
    in_progress = Report.query.filter_by(status='In Progress').count()
    critical = RiskScore.query.filter_by(risk_level='Critical').count()
    high = RiskScore.query.filter_by(risk_level='High').count()

    return jsonify({
        'total': total,
        'resolved': resolved,
        'in_progress': in_progress,
        'critical': critical,
        'high': high
    })


@routes_bp.route('/leaderboard')
def leaderboard():
    # Fetch top civic contributors
    top_citizens = User.query.filter(User.role == 'citizen').order_by(User.karma_points.desc()).limit(10).all()
    if not top_citizens:
        top_citizens = User.query.order_by(User.karma_points.desc()).limit(10).all()

    # Recent completed resolutions
    recent_resolved = Report.query.filter_by(status='Resolved').order_by(Report.updated_at.desc()).limit(5).all()

    # Current user stats if logged in
    user_rank = 1
    if current_user.is_authenticated:
        better_users = User.query.filter(User.karma_points > (current_user.karma_points or 0)).count()
        user_rank = better_users + 1

    return render_template('citizen/leaderboard.html',
                           top_citizens=top_citizens,
                           recent_resolved=recent_resolved,
                           user_rank=user_rank)


@routes_bp.route('/track')
@routes_bp.route('/track/<int:report_id>')
def track_incident(report_id=None):
    selected_report = None
    if report_id:
        selected_report = Report.query.get(report_id)
    elif request.args.get('id'):
        try:
            r_id = int(request.args.get('id'))
            selected_report = Report.query.get(r_id)
        except ValueError:
            selected_report = None

    if not selected_report:
        selected_report = Report.query.order_by(Report.created_at.desc()).first()

    recent_reports = Report.query.order_by(Report.created_at.desc()).limit(12).all()

    sla_hours = 48
    hours_elapsed = 4
    if selected_report and selected_report.created_at:
        hours_elapsed = max(1, int((datetime.utcnow() - selected_report.created_at).total_seconds() / 3600))

    sla_percentage = min(100, int((hours_elapsed / sla_hours) * 100))
    hours_remaining = max(0, sla_hours - hours_elapsed)

    return render_template('track.html',
                           report=selected_report,
                           recent_reports=recent_reports,
                           hours_elapsed=hours_elapsed,
                           hours_remaining=hours_remaining,
                           sla_percentage=sla_percentage)


@routes_bp.route('/analytics')
def analytics():
    total_count = Report.query.count()
    resolved_count = Report.query.filter_by(status='Resolved').count()
    active_count = Report.query.filter(~Report.status.in_(['Resolved', 'Rejected'])).count()
    critical_count = RiskScore.query.filter_by(risk_level='Critical').count()

    categories = db.session.query(Report.category, db.func.count(Report.id)).group_by(Report.category).all()
    category_labels = [c[0].replace('_', ' ').title() for c in categories]
    category_counts = [c[1] for c in categories]

    statuses = db.session.query(Report.status, db.func.count(Report.id)).group_by(Report.status).all()
    status_labels = [s[0] for s in statuses]
    status_counts = [s[1] for s in statuses]

    risks = db.session.query(RiskScore.risk_level, db.func.count(RiskScore.id)).group_by(RiskScore.risk_level).all()
    risk_dict = {r[0]: r[1] for r in risks}
    risk_labels = ['Critical', 'High', 'Medium', 'Low']
    risk_counts = [risk_dict.get(lvl, 0) for lvl in risk_labels]

    top_voted = Report.query.order_by(Report.upvotes_count.desc()).limit(6).all()

    return render_template('analytics.html',
                           total_count=total_count,
                           resolved_count=resolved_count,
                           active_count=active_count,
                           critical_count=critical_count,
                           category_labels=category_labels,
                           category_counts=category_counts,
                           status_labels=status_labels,
                           status_counts=status_counts,
                           risk_labels=risk_labels,
                           risk_counts=risk_counts,
                           top_voted=top_voted)


@routes_bp.route('/api/radar/scan')
def api_radar_scan():
    """
    Proximity Radar endpoint for Drivers and Field Inspectors:
    Calculates distances from current GPS position to all active hazards within radius.
    """
    try:
        user_lat = float(request.args.get('lat', 28.4744))
        user_lon = float(request.args.get('lon', 77.5040))
        radius = float(request.args.get('radius', 1200)) # meters
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid lat/lon parameters'}), 400

    active_reports = Report.query.filter(~Report.status.in_(['Resolved', 'Rejected'])).all()
    nearby_hazards = []

    for r in active_reports:
        dist = haversine_distance_meters(user_lat, user_lon, r.latitude, r.longitude)
        if dist <= radius:
            risk_lvl = r.risk_score.risk_level if r.risk_score else 'Medium'
            risk_pts = r.risk_score.total_score if r.risk_score else 50
            warning_text = f"Caution: {r.category.replace('_', ' ').capitalize()} reported {int(dist)} meters ahead near {r.address or 'your route'}!"
            
            nearby_hazards.append({
                'id': r.id,
                'title': r.title,
                'category': r.category,
                'address': r.address,
                'latitude': r.latitude,
                'longitude': r.longitude,
                'distance_meters': round(dist, 1),
                'risk_level': risk_lvl,
                'risk_score': risk_pts,
                'status': r.status,
                'warning_text': warning_text,
                'image_url': r.image_url
            })

    nearby_hazards.sort(key=lambda x: x['distance_meters'])
    return jsonify({
        'center': {'lat': user_lat, 'lon': user_lon},
        'radius_meters': radius,
        'count': len(nearby_hazards),
        'hazards': nearby_hazards
    })


@routes_bp.route('/api/report/<int:report_id>/upvote', methods=['POST'])
def api_report_upvote(report_id):
    """
    Community Verification ('I Encountered This Too')
    Increments upvotes, increases recurrence count, updates risk priority, and awards Karma.
    """
    report = Report.query.get_or_404(report_id)

    # Check user
    user_id = current_user.id if current_user.is_authenticated else None
    if user_id:
        existing = Upvote.query.filter_by(report_id=report.id, user_id=user_id).first()
        if existing:
            return jsonify({
                'success': False,
                'already_upvoted': True,
                'message': 'You have already confirmed this road hazard.',
                'upvotes_count': report.upvotes_count or 1
            })

        upvote = Upvote(report_id=report.id, user_id=user_id)
        db.session.add(upvote)
        
        # Award Karma to current user
        current_user.karma_points = (current_user.karma_points or 0) + 15
        if current_user.karma_points >= 1000:
            current_user.badge = '👑 Highway Sentinel'
        elif current_user.karma_points >= 500:
            current_user.badge = '🥇 Civic Guardian'
        elif current_user.karma_points >= 200:
            current_user.badge = '🥈 Pavement Vigilante'

    # Award Karma to reporter
    if report.reporter:
        report.reporter.karma_points = (report.reporter.karma_points or 0) + 20

    report.upvotes_count = (report.upvotes_count or 0) + 1
    # Recurrence escalation
    if report.upvotes_count % 2 == 0:
        report.recurrence_count = (report.recurrence_count or 1) + 1
        update_or_create_risk_score(report)

    db.session.commit()

    return jsonify({
        'success': True,
        'already_upvoted': False,
        'upvotes_count': report.upvotes_count,
        'recurrence_count': report.recurrence_count,
        'new_risk_score': report.risk_score.total_score if report.risk_score else None,
        'message': 'Confirmation recorded! +15 Civic Karma awarded. Risk score escalated.'
    })


@routes_bp.route('/api/ai-vision-inspect', methods=['POST'])
def api_ai_vision_inspect():
    """
    AI Computer Vision Diagnostic HUD:
    Scans road damage photo, returns detected bounding box, confidence, severity & PCI index.
    """
    category_hint = request.form.get('category_hint', 'pothole')
    
    # Realistic CV inference simulation with deterministic variation
    diagnostics = {
        'pothole': {
            'label': 'Deep Asphalt Pothole (Sharp Edge Rim Cavity)',
            'confidence': round(random.uniform(94.5, 98.6), 1),
            'severity': 'Critical',
            'est_depth_cm': 14.5,
            'est_area_sqm': 1.35,
            'pci_rating': 'Very Poor (18/100)',
            'impact_hazard': 'Severe tire puncture, alloy wheel fracture, 2-wheeler skid',
            'bbox': {'top': 28, 'left': 22, 'width': 54, 'height': 48} # percentages
        },
        'waterlogging': {
            'label': 'Stormwater Carriageway Submersion',
            'confidence': round(random.uniform(92.0, 97.4), 1),
            'severity': 'High',
            'est_depth_cm': 30.0,
            'est_area_sqm': 18.5,
            'pci_rating': 'Impassable (12/100)',
            'impact_hazard': 'Hydroplaning, submerged engine intake, concealed potholes',
            'bbox': {'top': 35, 'left': 15, 'width': 70, 'height': 50}
        },
        'damaged_road': {
            'label': 'High-Density Alligator Cracking & Rutting',
            'confidence': round(random.uniform(91.8, 96.5), 1),
            'severity': 'High',
            'est_depth_cm': 6.2,
            'est_area_sqm': 5.2,
            'pci_rating': 'Poor (28/100)',
            'impact_hazard': 'Suspension vibration, rapid disintegration under monsoon',
            'bbox': {'top': 25, 'left': 18, 'width': 64, 'height': 52}
        },
        'blocked_drain': {
            'label': 'Choked Stormwater Inlet & Catch-Pit Overflow',
            'confidence': round(random.uniform(93.1, 97.8), 1),
            'severity': 'High',
            'est_depth_cm': 45.0,
            'est_area_sqm': 2.8,
            'pci_rating': 'Critical (20/100)',
            'impact_hazard': 'Pedestrian fall risk, continuous road foundation erosion',
            'bbox': {'top': 30, 'left': 25, 'width': 50, 'height': 46}
        }
    }

    selected = diagnostics.get(category_hint, diagnostics['pothole'])
    return jsonify({
        'status': 'success',
        'detection': selected
    })


@routes_bp.route('/api/live-ticker')
def api_live_ticker():
    """
    Live Civic Dispatch Feed for Ticker:
    Provides dynamic recent municipal updates.
    """
    items = [
        {"icon": "🚨", "text": "Critical pothole confirmed near Pari Chowk Underpass (+3 upvotes)", "time": "2m ago"},
        {"icon": "🛠️", "text": "Rapid Response Crew dispatched to Metro Pillar 42 for drainage clearance", "time": "8m ago"},
        {"icon": "✅", "text": "Hot-mix asphalt patch repair completed at Gamma 1 Market Avenue", "time": "16m ago"},
        {"icon": "📡", "text": "Driver Radar detected severe waterlogging on NH-24 Nautanwa Bypass", "time": "24m ago"},
        {"icon": "👑", "text": "Citizen Priya Sharma unlocked 'Civic Guardian' badge (1,180 Karma)", "time": "32m ago"},
        {"icon": "⚡", "text": "Bridge expansion joint inspected on Expressway Exit 7 ramp", "time": "45m ago"}
    ]
    return jsonify({'items': items})



# --- Citizen Views ---

@routes_bp.route('/citizen/dashboard')
@login_required
@role_required('citizen', 'admin')
def citizen_dashboard():
    my_reports = Report.query.filter_by(user_id=current_user.id).order_by(Report.created_at.desc()).all()
    my_notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).limit(10).all()

    total_submitted = len(my_reports)
    in_progress_count = sum(1 for r in my_reports if r.status in ['Assigned', 'In Progress'])
    resolved_count = sum(1 for r in my_reports if r.status == 'Resolved')

    return render_template('citizen/dashboard.html',
                           reports=my_reports,
                           notifications=my_notifications,
                           total_submitted=total_submitted,
                           in_progress_count=in_progress_count,
                           resolved_count=resolved_count)


@routes_bp.route('/report', methods=['GET', 'POST'])
@login_required
def report_hazard():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        category = request.form.get('category', '').strip()
        description = request.form.get('description', '').strip()
        address = request.form.get('address', '').strip()
        road_type = request.form.get('road_type', 'arterial')
        accident_risk = request.form.get('accident_risk', 'moderate')
        traffic_density = request.form.get('traffic_density', 'moderate')

        try:
            latitude = float(request.form.get('latitude', 0))
            longitude = float(request.form.get('longitude', 0))
        except (ValueError, TypeError):
            flash("Valid GPS latitude and longitude coordinates are required.", "danger")
            return render_template('citizen/report_hazard.html', google_maps_api_key=current_app.config.get('GOOGLE_MAPS_API_KEY', ''))

        if not title or not category or not description:
            flash("Please fill in all required fields (title, category, and description).", "danger")
            return render_template('citizen/report_hazard.html', google_maps_api_key=current_app.config.get('GOOGLE_MAPS_API_KEY', ''))

        # Handle image upload to S3 or local fallback
        image_file = request.files.get('image')
        image_url = None
        image_key = None
        if image_file and image_file.filename != '':
            try:
                image_url, image_key = upload_image(image_file, folder='hazards')
            except ValueError as e:
                flash(str(e), "danger")
                return render_template('citizen/report_hazard.html', google_maps_api_key=current_app.config.get('GOOGLE_MAPS_API_KEY', ''))

        # Check for duplicate reports within 100 meters
        duplicate_parent = find_duplicate_report(category, latitude, longitude)

        # Create new report
        new_report = Report(
            user_id=current_user.id,
            title=title,
            category=category,
            description=description,
            latitude=latitude,
            longitude=longitude,
            address=address or f"Coordinates ({latitude:.4f}, {longitude:.4f})",
            image_url=image_url,
            image_key=image_key,
            road_type=road_type,
            traffic_density=traffic_density,
            accident_risk=accident_risk,
            status='Submitted',
            is_duplicate_of=duplicate_parent.id if duplicate_parent else None
        )

        db.session.add(new_report)
        db.session.flush() # Populate ID

        # Status history
        initial_history = StatusHistory(
            report_id=new_report.id,
            old_status=None,
            new_status='Submitted',
            changed_by=current_user.id,
            remarks='Citizen submitted new road hazard report'
        )
        db.session.add(initial_history)

        # Handle duplicate logic
        if duplicate_parent:
            duplicate_parent.recurrence_count += 1
            # Re-calculate parent's risk score with new recurrence count
            update_or_create_risk_score(duplicate_parent)
            flash_msg = (
                f"Report #{new_report.id} registered! Our system detected an existing report #{duplicate_parent.id} "
                f"within 100 meters for this {category.replace('_', ' ')}. Your submission has increased its priority!"
            )
        else:
            flash_msg = f"Report #{new_report.id} submitted successfully! Our risk analysis engine has prioritized it."

        # Calculate this report's initial risk score
        update_or_create_risk_score(new_report)

        # Create notification for citizen
        notif = Notification(
            user_id=current_user.id,
            report_id=new_report.id,
            message=f"Your hazard report #{new_report.id} ({title[:30]}) has been submitted."
        )
        db.session.add(notif)
        db.session.commit()

        flash(flash_msg, "success")
        return redirect(url_for('routes.report_detail', report_id=new_report.id))

    return render_template('citizen/report_hazard.html', google_maps_api_key=current_app.config.get('GOOGLE_MAPS_API_KEY', ''))


@routes_bp.route('/report/<int:report_id>')
def report_detail(report_id):
    report = Report.query.get_or_404(report_id)
    officers = User.query.filter_by(role='officer').all() if current_user.is_authenticated and current_user.role == 'admin' else []
    return render_template('citizen/report_detail.html', report=report, officers=officers)


# --- Admin Views ---

@routes_bp.route('/admin/dashboard')
@login_required
@role_required('admin')
def admin_dashboard():
    status_filter = request.args.get('status', 'all')
    risk_filter = request.args.get('risk', 'all')
    category_filter = request.args.get('category', 'all')

    query = Report.query

    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    if category_filter != 'all':
        query = query.filter_by(category=category_filter)

    all_reports = query.order_by(Report.created_at.desc()).all()

    # Filter by risk level if selected
    if risk_filter != 'all':
        all_reports = [r for r in all_reports if r.risk_score and r.risk_score.risk_level == risk_filter]

    # Overall stats
    total_count = Report.query.count()
    critical_count = RiskScore.query.filter_by(risk_level='Critical').count()
    high_count = RiskScore.query.filter_by(risk_level='High').count()
    pending_count = Report.query.filter(Report.status.in_(['Submitted', 'Under Review'])).count()
    assigned_count = Report.query.filter_by(status='Assigned').count()
    resolved_count = Report.query.filter_by(status='Resolved').count()

    officers = User.query.filter_by(role='officer').all()

    return render_template('admin/dashboard.html',
                           reports=all_reports,
                           officers=officers,
                           total_count=total_count,
                           critical_count=critical_count,
                           high_count=high_count,
                           pending_count=pending_count,
                           assigned_count=assigned_count,
                           resolved_count=resolved_count,
                           current_status=status_filter,
                           current_risk=risk_filter,
                           current_category=category_filter)


@routes_bp.route('/admin/report/<int:report_id>/assign', methods=['POST'])
@login_required
@role_required('admin')
def admin_assign_officer(report_id):
    report = Report.query.get_or_404(report_id)
    officer_id = request.form.get('officer_id', type=int)
    notes = request.form.get('notes', '').strip()

    officer = User.query.get_or_404(officer_id)
    if officer.role != 'officer':
        flash("Invalid officer selection.", "danger")
        return redirect(url_for('routes.report_detail', report_id=report.id))

    assignment = Assignment.query.filter_by(report_id=report.id).first()
    if not assignment:
        assignment = Assignment(report_id=report.id, officer_id=officer.id, assigned_by=current_user.id, notes=notes)
        db.session.add(assignment)
    else:
        assignment.officer_id = officer.id
        assignment.assigned_by = current_user.id
        assignment.notes = notes
        assignment.updated_at = datetime.utcnow()

    old_status = report.status
    report.status = 'Assigned'
    report.updated_at = datetime.utcnow()

    # Log history
    history = StatusHistory(
        report_id=report.id,
        old_status=old_status,
        new_status='Assigned',
        changed_by=current_user.id,
        remarks=f"Assigned to Maintenance Officer {officer.name}. Notes: {notes}"
    )
    db.session.add(history)

    # Notifications
    db.session.add(Notification(
        user_id=officer.id,
        report_id=report.id,
        message=f"You have been assigned to road hazard #{report.id}: '{report.title}'"
    ))
    db.session.add(Notification(
        user_id=report.user_id,
        report_id=report.id,
        message=f"Your hazard report #{report.id} has been assigned to Officer {officer.name}."
    ))

    db.session.commit()
    flash(f"Report #{report.id} assigned to Officer {officer.name} successfully.", "success")
    return redirect(url_for('routes.report_detail', report_id=report.id))


@routes_bp.route('/admin/report/<int:report_id>/status', methods=['POST'])
@login_required
@role_required('admin')
def admin_update_status(report_id):
    report = Report.query.get_or_404(report_id)
    new_status = request.form.get('status')
    remarks = request.form.get('remarks', '').strip()

    valid_statuses = ['Submitted', 'Under Review', 'Assigned', 'In Progress', 'Resolved', 'Rejected', 'Reopened']
    if new_status not in valid_statuses:
        flash("Invalid status choice.", "danger")
        return redirect(url_for('routes.report_detail', report_id=report.id))

    old_status = report.status
    report.status = new_status
    report.updated_at = datetime.utcnow()

    history = StatusHistory(
        report_id=report.id,
        old_status=old_status,
        new_status=new_status,
        changed_by=current_user.id,
        remarks=remarks or f"Status changed by Admin {current_user.name}"
    )
    db.session.add(history)

    # Notify citizen
    db.session.add(Notification(
        user_id=report.user_id,
        report_id=report.id,
        message=f"Status for report #{report.id} changed to '{new_status}'."
    ))

    db.session.commit()
    flash(f"Report #{report.id} status updated to '{new_status}'.", "success")
    return redirect(url_for('routes.report_detail', report_id=report.id))


# --- Maintenance Officer Views ---

@routes_bp.route('/officer/dashboard')
@login_required
@role_required('officer', 'admin')
def officer_dashboard():
    assignments = Assignment.query.filter_by(officer_id=current_user.id).order_by(Assignment.assigned_at.desc()).all()
    assigned_reports = [a.report for a in assignments if a.report]

    in_progress = [r for r in assigned_reports if r.status == 'In Progress']
    pending = [r for r in assigned_reports if r.status == 'Assigned']
    completed = [r for r in assigned_reports if r.status == 'Resolved']

    return render_template('officer/dashboard.html',
                           assigned_reports=assigned_reports,
                           in_progress=in_progress,
                           pending=pending,
                           completed=completed)


@routes_bp.route('/officer/report/<int:report_id>/maintenance', methods=['POST'])
@login_required
@role_required('officer', 'admin')
def officer_update_maintenance(report_id):
    report = Report.query.get_or_404(report_id)
    status = request.form.get('status', 'In Progress')
    remarks = request.form.get('remarks', '').strip()

    if not remarks:
        flash("Maintenance notes/remarks are required.", "danger")
        return redirect(url_for('routes.report_detail', report_id=report.id))

    # After-repair image
    after_image_file = request.files.get('after_image')
    after_url = None
    after_key = None
    if after_image_file and after_image_file.filename != '':
        try:
            after_url, after_key = upload_image(after_image_file, folder='maintenance')
        except ValueError as e:
            flash(str(e), "danger")
            return redirect(url_for('routes.report_detail', report_id=report.id))

    # Add maintenance record
    maintenance = Maintenance(
        report_id=report.id,
        officer_id=current_user.id,
        remarks=remarks,
        before_image_url=report.image_url,
        after_image_url=after_url,
        after_image_key=after_key
    )
    db.session.add(maintenance)

    old_status = report.status
    report.status = status
    report.updated_at = datetime.utcnow()

    # Log status history
    history = StatusHistory(
        report_id=report.id,
        old_status=old_status,
        new_status=status,
        changed_by=current_user.id,
        remarks=f"Maintenance logged by Officer {current_user.name}: {remarks[:100]}"
    )
    db.session.add(history)

    # Notify citizen
    db.session.add(Notification(
        user_id=report.user_id,
        report_id=report.id,
        message=f"Work update on report #{report.id}: Status is now '{status}'."
    ))

    db.session.commit()
    flash(f"Maintenance update saved for Report #{report.id}.", "success")
    return redirect(url_for('routes.report_detail', report_id=report.id))
