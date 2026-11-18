import math
from app.models import Report, RiskScore
from app.database import db

# Distance threshold for duplicate detection in meters
DUPLICATE_RADIUS_METERS = 100.0

def haversine_distance_meters(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees) in meters.
    """
    R = 6371000.0 # Earth's radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * \
        math.sin(delta_lambda / 2.0) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def find_duplicate_report(category, latitude, longitude):
    """
    Checks unresolved reports with the same category within DUPLICATE_RADIUS_METERS.
    Returns the parent Report if found, else None.
    """
    # Exclude resolved and rejected reports, and only look for primary reports (is_duplicate_of is None)
    candidates = Report.query.filter(
        Report.category == category,
        Report.is_duplicate_of.is_(None),
        ~Report.status.in_(['Resolved', 'Rejected'])
    ).all()

    for cand in candidates:
        dist = haversine_distance_meters(latitude, longitude, cand.latitude, cand.longitude)
        if dist <= DUPLICATE_RADIUS_METERS:
            return cand
    return None


def calculate_risk_score(category, road_type='arterial', traffic_density='moderate', accident_risk='moderate', recurrence_count=1):
    """
    Calculate the comprehensive Risk Score (0-100) based on:
    1. Severity (max 40)
    2. Location Impact (max 20)
    3. Safety Impact (max 25)
    4. Recurrence (max 15)
    """
    # 1. Severity points (Max 40)
    category_severity_map = {
        'pothole': 35,
        'damaged_road': 30,
        'waterlogging': 28,
        'blocked_drain': 24,
        'broken_streetlight': 18,
        'damaged_sign': 16,
        'other': 30
    }
    severity_pts = category_severity_map.get(category.lower(), 15)

    # 2. Location Impact points (Max 20)
    road_type_map = {
        'highway': 20,
        'school_zone': 18,
        'hospital_zone': 18,
        'arterial': 15,
        'commercial': 14,
        'residential': 8,
        'rural': 6
    }
    location_pts = road_type_map.get(road_type.lower(), 10)

    # 3. Safety Impact points (Max 25)
    accident_risk_map = {
        'high': 25,
        'moderate': 15,
        'low': 7
    }
    safety_pts = accident_risk_map.get(accident_risk.lower(), 12)

    # 4. Recurrence points (Max 15)
    if recurrence_count <= 1:
        recurrence_pts = 0
    elif recurrence_count == 2:
        recurrence_pts = 5
    elif recurrence_count == 3:
        recurrence_pts = 10
    else:
        recurrence_pts = 15 # Cap at 15

    total = severity_pts + location_pts + safety_pts + recurrence_pts
    total = min(100, max(0, total))

    # Determine risk category
    if total >= 80:
        risk_level = 'Critical'
    elif total >= 60:
        risk_level = 'High'
    elif total >= 30:
        risk_level = 'Medium'
    else:
        risk_level = 'Low'

    return {
        'severity_score': severity_pts,
        'location_impact_score': location_pts,
        'safety_impact_score': safety_pts,
        'recurrence_score': recurrence_pts,
        'total_score': total,
        'risk_level': risk_level
    }


def update_or_create_risk_score(report):
    """
    Computes and persists or updates the RiskScore record for a given report.
    """
    scores = calculate_risk_score(
        category=report.category,
        road_type=report.road_type or 'arterial',
        traffic_density=report.traffic_density or 'moderate',
        accident_risk=report.accident_risk or 'moderate',
        recurrence_count=report.recurrence_count or 1
    )

    risk_score = RiskScore.query.filter_by(report_id=report.id).first()
    if not risk_score:
        risk_score = RiskScore(report_id=report.id)
        db.session.add(risk_score)

    risk_score.severity_score = scores['severity_score']
    risk_score.location_impact_score = scores['location_impact_score']
    risk_score.safety_impact_score = scores['safety_impact_score']
    risk_score.recurrence_score = scores['recurrence_score']
    risk_score.total_score = scores['total_score']
    risk_score.risk_level = scores['risk_level']
    
    db.session.commit()
    return risk_score
