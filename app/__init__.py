import os
from flask import Flask
from app.config import Config
from app.database import db
from app.auth import login_manager, auth_bp
from app.routes import routes_bp
from app.models import User, Hazard, Report, RiskScore, StatusHistory, Assignment, Maintenance
from app.risk_engine import update_or_create_risk_score

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(routes_bp)

    # Ensure upload directory exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(os.path.join(app.root_path, 'static', 'img', 'hazards'), exist_ok=True)

    with app.app_context():
        db.create_all()
        seed_initial_data()

    return app


def seed_initial_data():
    """
    Seeds initial system categories, sample users (Admin, Officer, Citizen),
    and a rich set of 18 realistic road hazard reports across Greater Noida, NCR, and Nautanwa NH24.
    """
    # 1. Seed Hazard categories
    categories = [
        ('Severe Pothole', 'pothole', 'Deep road crater causing tire punctures and rim damage', 'High', 35),
        ('Damaged / Broken Asphalt', 'damaged_road', 'Cracked, caved in or uneven road surface', 'Medium', 30),
        ('Severe Waterlogging', 'waterlogging', 'Stagnant rainwater submerging the carriageway', 'High', 28),
        ('Blocked Stormwater Drain', 'blocked_drain', 'Debris or silt choking road drainage lines', 'Medium', 24),
        ('Broken Streetlight Pole', 'broken_streetlight', 'Unlit road segment or damaged electric pole', 'Low', 18),
        ('Damaged Traffic Sign', 'damaged_sign', 'Missing or distorted speed / directional sign', 'Low', 16),
        ('Missing Manhole / Open Hazard', 'other', 'Open drainage manhole or bent metal crash guardrail', 'High', 30),
    ]

    for title, cat, desc, sev, score in categories:
        h = Hazard.query.filter_by(category=cat).first()
        if not h:
            h = Hazard(title=title, category=cat, description=desc, default_severity=sev, base_severity_score=score)
            db.session.add(h)

    # 2. Seed Default Users with Civic Karma & Badges
    users_to_seed = [
        ('Administrator', 'admin@pavepulse.org', 'Admin@123', 'admin', '+91 98765 00001', 2500, '👑 Highway Sentinel'),
        ('Inspector Rajesh Kumar', 'officer@pavepulse.org', 'Officer@123', 'officer', '+91 98765 00002', 1800, '👑 Highway Sentinel'),
        ('Anita Sharma', 'citizen@pavepulse.org', 'Citizen@123', 'citizen', '+91 98765 00003', 480, '🥈 Pavement Vigilante'),
        ('Rajesh Verma', 'rajesh.verma@gmail.com', 'Citizen@123', 'citizen', '+91 98765 00004', 1420, '👑 Highway Sentinel'),
        ('Priya Sharma', 'priya.sharma@outlook.com', 'Citizen@123', 'citizen', '+91 98765 00005', 1180, '🥇 Civic Guardian'),
        ('Amit Patel', 'amit.patel@yahoo.com', 'Citizen@123', 'citizen', '+91 98765 00006', 950, '🥈 Pavement Vigilante'),
    ]

    created_users = {}
    for name, email, pwd, role, phone, karma, badge in users_to_seed:
        user = User.query.filter_by(email=email).first()
        if not user:
            user = User(name=name, email=email, role=role, phone=phone, karma_points=karma, badge=badge)
            user.set_password(pwd)
            db.session.add(user)
            db.session.flush()
        else:
            user.karma_points = karma
            user.badge = badge
        created_users[role] = user

    # 3. Seed 25 Realistic Reports if under 25 reports
    if Report.query.count() < 25:
        admin_u = created_users['admin']
        officer_u = created_users['officer']
        citizen_u = created_users['citizen']

        # Clear existing seed reports to cleanly recreate rich realistic dataset with genuine road photos
        Report.query.delete()
        RiskScore.query.delete()
        Assignment.query.delete()
        Maintenance.query.delete()
        StatusHistory.query.delete()
        db.session.commit()

        # Authentic local road hazard photos
        IMG_POTHOLE = '/static/img/hazards/pothole_1.jpg'
        IMG_WATER = '/static/img/hazards/waterlogging_1.jpg'
        IMG_ROAD = '/static/img/hazards/damaged_road_1.jpg'
        IMG_MANHOLE = '/static/img/hazards/open_manhole_1.jpg'
        IMG_GUARDRAIL = '/static/img/hazards/damaged_guardrail_1.jpg'
        IMG_REPAIRED = '/static/img/hazards/repaired_road_1.jpg'

        sample_reports = [
            # 1. Pari Chowk Underpass
            {
                'title': 'Crater-sized pothole with scattered loose gravel near Pari Chowk Underpass',
                'category': 'pothole',
                'description': 'Massive 1.8-meter wide crater in the fast lane right at underpass entry. Sharp asphalt edges causing multiple two-wheeler rim bends and sudden braking pileups during rush hour.',
                'lat': 28.4744,
                'lon': 77.5040,
                'address': 'Pari Chowk Circle, Sector Alpha 1, Greater Noida',
                'road_type': 'highway',
                'traffic_density': 'high',
                'accident_risk': 'high',
                'status': 'In Progress',
                'recurrence_count': 3,
                'image_url': IMG_POTHOLE
            },
            # 2. Metro Pillar 42
            {
                'title': 'Submerged carriageway and heavy monsoon waterlogging at Metro Pillar 42',
                'category': 'waterlogging',
                'description': 'Over 2.5 feet of stagnant dark storm runoff across both arterial lanes. Road divider concrete kerbs completely hidden, forcing motorists onto footpaths.',
                'lat': 28.4680,
                'lon': 77.4985,
                'address': 'Noida-Greater Noida Link Road, Metro Pillar 42',
                'road_type': 'arterial',
                'traffic_density': 'high',
                'accident_risk': 'high',
                'status': 'Assigned',
                'recurrence_count': 3,
                'image_url': IMG_WATER
            },
            # 3. Alpha 1 Commercial Belt
            {
                'title': 'Missing heavy iron stormwater manhole cover on Alpha 1 Commercial Belt',
                'category': 'other',
                'description': 'Exposed 4-foot deep stormwater drain opening on road shoulder without warning signs or barricades. Extreme fall danger to school children, pedestrians, and cyclists.',
                'lat': 28.4770,
                'lon': 77.5090,
                'address': 'Commercial Belt Inner Loop, Sector Alpha 1, Greater Noida',
                'road_type': 'arterial',
                'traffic_density': 'high',
                'accident_risk': 'high',
                'status': 'Under Review',
                'recurrence_count': 3,
                'image_url': IMG_MANHOLE
            },
            # 4. Expressway Flyover
            {
                'title': 'Cracked bridge expansion joint on Noida-Greater Noida Expressway Exit 7',
                'category': 'damaged_road',
                'description': 'Expansion joint steel comb plate dislodged and protruding 4cm above tarmac level. High-speed highway vehicles experiencing severe tire puncture and vehicle control risk.',
                'lat': 28.4910,
                'lon': 77.4890,
                'address': 'Expressway Flyover Ramp, Knowledge Park I Exit',
                'road_type': 'highway',
                'traffic_density': 'high',
                'accident_risk': 'high',
                'status': 'Assigned',
                'recurrence_count': 2,
                'image_url': IMG_ROAD
            },
            # 5. DPS Knowledge Park
            {
                'title': 'Deep sunken trench and collapsed asphalt at DPS Knowledge Park II',
                'category': 'damaged_road',
                'description': 'Utility pipeline trench collapsed 25cm deep directly at school bus boarding bay. Buses scraping undercarriage; students at risk while crossing.',
                'lat': 28.4820,
                'lon': 77.5120,
                'address': 'Institutional Area, Knowledge Park II, Greater Noida',
                'road_type': 'school_zone',
                'traffic_density': 'moderate',
                'accident_risk': 'high',
                'status': 'Submitted',
                'recurrence_count': 1,
                'image_url': IMG_ROAD
            },
            # 6. Grand Venice Mall
            {
                'title': 'Collapsed catch-pit drain causing mud and silt overflow opposite Grand Venice',
                'category': 'blocked_drain',
                'description': 'Stormwater inlet choked with building gravel and silt. Muddy water spilling across 3 traffic lanes causing two-wheelers to slip on oily mud.',
                'lat': 28.4650,
                'lon': 77.5150,
                'address': 'Kasna Road, Opposite Grand Venice Mall Entry Gate',
                'road_type': 'commercial',
                'traffic_density': 'high',
                'accident_risk': 'moderate',
                'status': 'In Progress',
                'recurrence_count': 2,
                'image_url': IMG_WATER
            },
            # 7. Sector Omega 1 Guardrail
            {
                'title': 'Crumpled steel highway crash barrier with protruding sharp jagged edge',
                'category': 'other',
                'description': 'W-beam metal guardrail crushed in recent collision; twisted steel beam juts 1 meter into the active travel lane.',
                'lat': 28.4550,
                'lon': 77.4950,
                'address': 'Sector Omega 1 Main Peripheral Road',
                'road_type': 'arterial',
                'traffic_density': 'moderate',
                'accident_risk': 'high',
                'status': 'Assigned',
                'recurrence_count': 1,
                'image_url': IMG_GUARDRAIL
            },
            # 8. Nautanwa - Sonauli NH24 Highway
            {
                'title': 'Multiple deep crater potholes along Nautanwa-Sonauli NH24 Highway',
                'category': 'pothole',
                'description': 'Heavy cargo truck traffic has ground the asphalt into a 2-meter cluster of continuous potholes near the border corridor. Night drivers swerving dangerously into oncoming traffic.',
                'lat': 27.4285,
                'lon': 83.4210,
                'address': 'National Highway 24, Near Nautanwa Toll Gate, Maharajganj',
                'road_type': 'highway',
                'traffic_density': 'high',
                'accident_risk': 'high',
                'status': 'Assigned',
                'recurrence_count': 3,
                'image_url': IMG_POTHOLE
            },
            # 9. Nautanwa Railway Crossing
            {
                'title': 'Severe waterlogging and muddy slush at Nautanwa Railway Station Road',
                'category': 'waterlogging',
                'description': 'Road near railway overbridge flooded with 1.5 feet of muddy rainwater. Pedestrians unable to reach station entrance without walking through contaminated water.',
                'lat': 27.4240,
                'lon': 83.4150,
                'address': 'Station Road, Near Nautanwa Railway Crossing, Maharajganj',
                'road_type': 'commercial',
                'traffic_density': 'high',
                'accident_risk': 'moderate',
                'status': 'In Progress',
                'recurrence_count': 2,
                'image_url': IMG_WATER
            },
            # 10. Nautanwa Main Market
            {
                'title': 'Open sewer drainage channel without stone slab on Nautanwa Market Road',
                'category': 'other',
                'description': 'Concrete drain covering broken for 2 weeks in busy market lane. Multiple two-wheelers fell in during evening shopping hours.',
                'lat': 27.4224,
                'lon': 83.4113,
                'address': 'Main Market Avenue, Ward No 4, Nautanwa, Maharajganj',
                'road_type': 'commercial',
                'traffic_density': 'high',
                'accident_risk': 'high',
                'status': 'Under Review',
                'recurrence_count': 2,
                'image_url': IMG_MANHOLE
            },
            # 11. Surajpur Road
            {
                'title': 'Extinguished high-mast streetlighting array creating dark blind turn',
                'category': 'broken_streetlight',
                'description': 'All 6 floodlamps on high-mast tower dead for over 12 days. Heavy container trucks navigating unlit S-curve in complete darkness.',
                'lat': 28.4580,
                'lon': 77.5030,
                'address': 'Surajpur Industrial Area Entry Curve, Greater Noida',
                'road_type': 'arterial',
                'traffic_density': 'high',
                'accident_risk': 'moderate',
                'status': 'In Progress',
                'recurrence_count': 1,
                'image_url': IMG_POTHOLE
            },
            # 12. Sharda University Gate 4
            {
                'title': 'Distorted 40 km/h speed limit sign obscured by dense thorny brush',
                'category': 'damaged_sign',
                'description': 'Reflective aluminum speed regulatory sign twisted backwards and completely buried in wild overgrown shrubs near student crossing.',
                'lat': 28.4880,
                'lon': 77.5200,
                'address': 'Knowledge Park III, Near Sharda University Gate 4',
                'road_type': 'school_zone',
                'traffic_density': 'moderate',
                'accident_risk': 'low',
                'status': 'Submitted',
                'recurrence_count': 1,
                'image_url': IMG_ROAD
            },
            # 13. Sector Beta 2 Bitumen Erosion
            {
                'title': 'Continuous sewage backflow dissolving road bitumen surface on Beta 2',
                'category': 'waterlogging',
                'description': 'Acidic sewer overflow peeling off top bitumen layer over a 50-meter section, exposing loose sharp ballast stones.',
                'lat': 28.4715,
                'lon': 77.4920,
                'address': 'Sector Beta 2, Road No. 4, Opposite Club House, Greater Noida',
                'road_type': 'residential',
                'traffic_density': 'moderate',
                'accident_risk': 'moderate',
                'status': 'Under Review',
                'recurrence_count': 1,
                'image_url': IMG_WATER
            },
            # 14. Sector Delta 1 Electrical Hazard
            {
                'title': 'Tilted steel streetlight pole with exposed wiring near children playground',
                'category': 'broken_streetlight',
                'description': 'Pole struck by utility truck and leaning at 45-degree angle. Base junction box cover missing with live insulated cable exposed.',
                'lat': 28.4850,
                'lon': 77.5060,
                'address': 'Sector Delta 1 Central Park Peripheral Road',
                'road_type': 'residential',
                'traffic_density': 'low',
                'accident_risk': 'high',
                'status': 'Assigned',
                'recurrence_count': 1,
                'image_url': IMG_ROAD
            },
            # 15. Kasna Village Culvert Collapse
            {
                'title': 'Collapsed brick culvert wing wall causing road shoulder drop-off',
                'category': 'blocked_drain',
                'description': 'Underground culvert structure caved in, eating 1 meter into the blacktop asphalt carriageway. Heavy erosion occurring.',
                'lat': 28.4520,
                'lon': 77.5310,
                'address': 'Kasna Main Village Road, Near Community Health Centre',
                'road_type': 'arterial',
                'traffic_density': 'moderate',
                'accident_risk': 'high',
                'status': 'Assigned',
                'recurrence_count': 1,
                'image_url': IMG_MANHOLE
            },
            # 16. Sector Chi 2 Median Reflector Damage
            {
                'title': 'Missing road divider reflector markers causing night collision hazard',
                'category': 'damaged_sign',
                'description': 'Unlit concrete divider median has zero reflective cat-eyes over 400-meter stretch. Cars frequently clipping median edge at night.',
                'lat': 28.4410,
                'lon': 77.4850,
                'address': 'Sector Chi 2 Main Boulevard, Greater Noida',
                'road_type': 'arterial',
                'traffic_density': 'moderate',
                'accident_risk': 'moderate',
                'status': 'Submitted',
                'recurrence_count': 1,
                'image_url': IMG_GUARDRAIL
            },
            # 17. RESOLVED Case 1: Surajpur High-Voltage Pole Restoration
            {
                'title': 'Storm-uprooted streetlight pole restored and wire conduit insulated',
                'category': 'broken_streetlight',
                'description': 'Uprooted 8-meter pole safely removed, replacement LED fixture installed, and power conduit sealed.',
                'lat': 28.4605,
                'lon': 77.5010,
                'address': 'Surajpur Main Road, Near Police Post, Greater Noida',
                'road_type': 'arterial',
                'traffic_density': 'moderate',
                'accident_risk': 'moderate',
                'status': 'Resolved',
                'recurrence_count': 1,
                'image_url': IMG_ROAD,
                'resolved_img': IMG_REPAIRED,
                'resolved_remarks': 'Damaged pole replaced with high-strength galvanized steel pole. Circuit tested and energized. Roadway clear.'
            },
            # 18. RESOLVED Case 2: Gamma 1 Market Crater Pothole Bitumen Patch
            {
                'title': 'Severe crater pothole restored with hot-mix asphalt compaction',
                'category': 'pothole',
                'description': 'Deep 15cm pothole filled, leveled, and roller-compacted with high-grade bitumen asphalt.',
                'lat': 28.4700,
                'lon': 77.5070,
                'address': 'Sector Gamma 1 Market Avenue, Near Community Centre',
                'road_type': 'commercial',
                'traffic_density': 'moderate',
                'accident_risk': 'moderate',
                'status': 'Resolved',
                'recurrence_count': 1,
                'upvotes_count': 6,
                'image_url': IMG_POTHOLE,
                'resolved_img': IMG_REPAIRED,
                'resolved_remarks': 'Excavated loose debris, applied tack coat, filled with 60kg hot-mix asphalt and compacted with roller. Barricades removed.'
            },
            # 19. Yamuna Expressway Zero Point
            {
                'title': 'High-speed pothole cavity near Yamuna Expressway Zero Point Toll Approach',
                'category': 'pothole',
                'description': 'Deep sharp-edged depression in lane 2 right before toll plaza approach. Vehicles braking abruptly from 100 km/h causing near-miss rear-end pileups.',
                'lat': 28.4620,
                'lon': 77.5280,
                'address': 'Yamuna Expressway Zero Point Interchange, Greater Noida',
                'road_type': 'highway',
                'traffic_density': 'high',
                'accident_risk': 'high',
                'status': 'Assigned',
                'recurrence_count': 4,
                'upvotes_count': 12,
                'image_url': IMG_POTHOLE
            },
            # 20. Noida Expressway Km 12
            {
                'title': 'Longitudinal surface fracture and loose asphalt aggregate at Km 12',
                'category': 'damaged_road',
                'description': 'Severe 80-meter asphalt tearing with flying gravel hitting windshields of following highway traffic.',
                'lat': 28.5150,
                'lon': 77.4200,
                'address': 'Noida-Greater Noida Expressway, Milestone Km 12 Southbound',
                'road_type': 'highway',
                'traffic_density': 'high',
                'accident_risk': 'high',
                'status': 'In Progress',
                'recurrence_count': 3,
                'upvotes_count': 9,
                'image_url': IMG_ROAD
            },
            # 21. Sector 62 Noida Underpass
            {
                'title': 'Underpass road basin flooded with 2 feet of storm runoff near Model Town',
                'category': 'waterlogging',
                'description': 'Automated sump pumps non-operational. Waterlogged underpass blocking traffic flow between Indirapuram and Noida IT parks.',
                'lat': 28.6250,
                'lon': 77.3650,
                'address': 'Model Town Crossing Underpass, Sector 62, Noida',
                'road_type': 'arterial',
                'traffic_density': 'high',
                'accident_risk': 'high',
                'status': 'Assigned',
                'recurrence_count': 3,
                'upvotes_count': 15,
                'image_url': IMG_WATER
            },
            # 22. Gaur City 1 Roundabout
            {
                'title': 'Broken cast iron storm drain grating on Gaur City 1 Commercial Ring',
                'category': 'blocked_drain',
                'description': 'Heavy vehicle collapsed drainage grate. 3-foot exposed pit in busy market roundabout causing major traffic gridlock.',
                'lat': 28.6080,
                'lon': 77.4280,
                'address': 'Gaur City 1 Commercial Roundabout, Greater Noida West',
                'road_type': 'commercial',
                'traffic_density': 'high',
                'accident_risk': 'high',
                'status': 'Submitted',
                'recurrence_count': 2,
                'upvotes_count': 7,
                'image_url': IMG_MANHOLE
            },
            # 23. DND Flyway Toll Plaza Merge
            {
                'title': 'Crumpled impact-attenuator crash barrier post-collision on DND Ramp',
                'category': 'other',
                'description': 'Steel guardrail crushed into active lane 1. Protruding sharp W-beam hazard for high-speed merging vehicles.',
                'lat': 28.5700,
                'lon': 77.2950,
                'address': 'DND Flyway Toll Plaza Approach Ramp, Delhi-Noida Border',
                'road_type': 'highway',
                'traffic_density': 'high',
                'accident_risk': 'high',
                'status': 'Under Review',
                'recurrence_count': 2,
                'upvotes_count': 5,
                'image_url': IMG_GUARDRAIL
            },
            # 24. Nautanwa Bypass
            {
                'title': 'Heavy Indo-Nepal container truck rutting creating 10cm asphalt ridges',
                'category': 'damaged_road',
                'description': 'Continuous wheel ruts from overloaded trucks. Sedans scraping undercarriage and two-wheelers losing balance.',
                'lat': 27.4350,
                'lon': 83.4280,
                'address': 'NH-24 Nautanwa Bypass Road, Near Sonauli Cargo Terminal',
                'road_type': 'highway',
                'traffic_density': 'high',
                'accident_risk': 'high',
                'status': 'Assigned',
                'recurrence_count': 4,
                'upvotes_count': 11,
                'image_url': IMG_ROAD
            },
            # 25. Pharenda Crossing Approach
            {
                'title': 'Collapsed asphalt shoulder and crater pothole at Pharenda Railway Overbridge',
                'category': 'pothole',
                'description': 'Sub-base soil washed away by monsoon rain, causing edge blacktop to crack and cave inward 35cm deep.',
                'lat': 27.3100,
                'lon': 83.2800,
                'address': 'State Highway 1A, Pharenda Railway Overbridge West Approach',
                'road_type': 'highway',
                'traffic_density': 'moderate',
                'accident_risk': 'high',
                'status': 'In Progress',
                'recurrence_count': 2,
                'upvotes_count': 8,
                'image_url': IMG_POTHOLE
            }
        ]

        for s in sample_reports:
            rep = Report(
                user_id=citizen_u.id,
                title=s['title'],
                category=s['category'],
                description=s['description'],
                latitude=s['lat'],
                longitude=s['lon'],
                address=s['address'],
                road_type=s['road_type'],
                traffic_density=s['traffic_density'],
                accident_risk=s['accident_risk'],
                status=s['status'],
                recurrence_count=s.get('recurrence_count', 1),
                upvotes_count=s.get('upvotes_count', 3),
                image_url=s['image_url']
            )
            db.session.add(rep)
            db.session.flush()

            # Status history record
            hist = StatusHistory(
                report_id=rep.id,
                old_status=None,
                new_status=s['status'],
                changed_by=admin_u.id,
                remarks='Civic hazard audit verified and logged into system'
            )
            db.session.add(hist)

            # Assign officer to non-submitted reports
            if s['status'] in ['Assigned', 'In Progress', 'Resolved']:
                assign = Assignment(
                    report_id=rep.id,
                    officer_id=officer_u.id,
                    assigned_by=admin_u.id,
                    notes='High priority repair assignment dispatched.'
                )
                db.session.add(assign)

            # Add resolved maintenance proof for resolved reports
            if s['status'] == 'Resolved':
                maint = Maintenance(
                    report_id=rep.id,
                    officer_id=officer_u.id,
                    remarks=s.get('resolved_remarks', 'Repaired with asphalt compaction.'),
                    before_image_url=s['image_url'],
                    after_image_url=s.get('resolved_img', IMG_REPAIRED)
                )
                db.session.add(maint)

            # Calculate risk score
            update_or_create_risk_score(rep)

        db.session.commit()
