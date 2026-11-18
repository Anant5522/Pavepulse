# PavePulse – Cloud-Native Road Hazard Reporting and Monitoring Platform

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0%2B-green.svg)](https://flask.palletsprojects.com/)
[![MySQL](https://img.shields.io/badge/Database-MySQL%20%2F%20SQLite-orange.svg)](https://www.mysql.com/)
[![AWS](https://img.shields.io/badge/Cloud-AWS%20EC2%20%2B%20S3-yellow.svg)](https://aws.amazon.com/)
[![License](https://img.shields.io/badge/License-MIT-lightgrey.svg)](LICENSE)

**PavePulse** is a complete, cloud-hosted civic infrastructure platform designed to bridge the gap between citizens encountering hazardous road defects (potholes, severe waterlogging, damaged asphalt, missing signage) and municipal road maintenance authorities.

---

## 🌟 Key Features

1. **Role-Based Workflows**:
   - **Citizen**: Submit hazard reports with GPS location, photo uploads, track resolution status.
   - **Maintenance Officer**: View assigned hazards, update status to *In Progress* / *Resolved*, upload after-repair photographic evidence.
   - **Administrator**: Full operations dashboard, GIS hazard map, risk-priority queue, officer assignment.
2. **Automated Risk Scoring Engine**:
   - Calculates a prioritized 0–100 risk score based on **Severity (40 pts)**, **Location Impact (20 pts)**, **Safety Threat (25 pts)**, and **Recurrence (15 pts)**.
   - Classifies hazards into **Critical (80–100)**, **High (60–79)**, **Medium (30–59)**, and **Low (0–29)**.
3. **Smart Duplicate Detection**:
   - Compares GPS coordinates using the **Haversine formula** within ~100 meters.
   - Automatically clusters recurring complaints, increases recurrence score, and elevates priority without discarding individual citizen voices.
4. **Interactive Geospatial Map**:
   - Built with **Leaflet.js** and **OpenStreetMap**.
   - Dynamic color-coded markers reflecting live risk levels.
   - Search and filter by category, status, and severity.
5. **Dual-Mode Cloud Object Storage (Amazon S3)**:
   - Integrates with Amazon S3 for cloud photo storage using an **EC2 IAM Instance Role** (zero hardcoded credentials).
   - Seamless local filesystem fallback for offline development.

---

## 🏗️ Architecture

```
                       +-------------------+
                       |  Web Browser / UI |
                       |  (Leaflet + CSS)  |
                       +---------+---------+
                                 | HTTP / HTTPS
                                 v
                       +-------------------+
                       |    Nginx Proxy    |
                       |   (Port 80/443)   |
                       +---------+---------+
                                 | Reverse Proxy
                                 v
                       +-------------------+
                       |   Gunicorn/Flask  |
                       |   (Port 5000)     |
                       +---+-----------+---+
                           |           |
            IAM Role / S3  |           | PyMySQL (Port 3306)
                           v           v
           +-----------------+       +-------------------+
           |    Amazon S3    |       |   MySQL Server    |
           |  (Photos/Proof) |       |  (pavepulse_db)   |
           +-----------------+       +-------------------+
```

---

## 🚀 Quickstart: Running Locally

```bash
# 1. Clone repository & change directory
cd pavepulse

# 2. Create virtual environment
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run application
python run.py
```

The database initializes automatically with SQLite and pre-seeds sample users and hazards. Open [http://localhost:5000](http://localhost:5000) in your browser.

### Default Seed Accounts:
- **Admin**: `admin@pavepulse.org` / `Admin@123`
- **Officer**: `officer@pavepulse.org` / `Officer@123`
- **Citizen**: `citizen@pavepulse.org` / `Citizen@123`

---

## ☁️ Deploying to AWS (Free Tier Blueprint)

For step-by-step instructions on launching a free `t2.micro` or `t3.micro` EC2 instance, creating an S3 bucket, setting up IAM instance roles, and running the 1-command deployment script `deploy/setup_ec2.sh`, see:

👉 **[AWS_DEPLOYMENT_GUIDE.md](AWS_DEPLOYMENT_GUIDE.md)**
