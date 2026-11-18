# 🌐 PavePulse – AWS Free Tier Deployment Guide

This comprehensive, step-by-step blueprint shows you how to host **PavePulse** on **Amazon Web Services (AWS)** while keeping your costs **$0.00** (strictly within AWS Free Tier limits).

---

## 🛡️ Golden Rules: How to Keep AWS 100% Free

To prevent unexpected billing on AWS, strictly adhere to these rules:

| Do's (Free Tier Safe) | Don'ts (Cost Traps) |
| :--- | :--- |
| ✅ Use a single `t2.micro` or `t3.micro` instance (750 free hours/month) | ❌ **Do NOT create an Application Load Balancer (ALB)** (~$18–$25/mo) |
| ✅ Keep MySQL on the same EC2 instance | ❌ **Do NOT create a NAT Gateway** (~$35/mo) |
| ✅ Allocate **20 GB or 30 GB** EBS Storage (gp3) (Free tier permits up to 30 GB) | ❌ Do not allocate > 30 GB EBS or create unattached volume snapshots |
| ✅ Store images in Amazon S3 (5 GB free standard storage) | ❌ Do not launch multiple simultaneous EC2 instances |
| ✅ Attach an **IAM Instance Role** to EC2 for S3 permissions | ❌ Never hardcode AWS Access Keys in source code or GitHub |
| ✅ Set up an **AWS Budget Alert for \$1.00** | ❌ Never leave test resources running indefinitely if no longer needed |

---

## Step 1: Set Up Billing Alerts on AWS (2 Minutes)

1. Log in to the [AWS Management Console](https://console.aws.amazon.com/).
2. In the top search bar, type **Budgets** and click **AWS Budgets**.
3. Click **Create budget** &rarr; Select **Cost budget (Recommended)**.
4. Set:
   - **Budget amount**: `$1.00`
   - **Email notifications**: Enter your personal email address.
5. Click **Create budget**. AWS will now email you immediately if any charges reach even \$1.

---

## Step 2: Create an Amazon S3 Bucket for Road Hazard Images

1. Search for **S3** in the AWS Console.
2. Click **Create bucket**.
3. Configure:
   - **Bucket name**: `pavepulse-hazards-[your-initials]-[random-number]` (e.g., `pavepulse-hazards-anant-2026`).
   - **AWS Region**: `ap-south-1` (Asia Pacific - Mumbai) or your closest region.
   - **Object Ownership**: ACLs disabled (recommended).
   - **Block Public Access**: Keep **"Block all public access" checked**.
4. Click **Create bucket**.

---

## Step 3: Create an IAM Role for EC2 (No Hardcoded Keys!)

Using an IAM Role allows your EC2 server to securely upload photographs to Amazon S3 without needing access keys or secrets in your `.env` file.

1. Search for **IAM** in the AWS Console.
2. In the left navigation, click **Roles** &rarr; **Create role**.
3. Select **AWS service** &rarr; Use case: **EC2** &rarr; Click **Next**.
4. In the permissions search box, search for: `AmazonS3FullAccess` (or create a custom inline policy for your specific bucket).
5. Check the box next to `AmazonS3FullAccess` &rarr; Click **Next**.
6. **Role name**: `PavePulse-EC2-S3-Role`.
7. Click **Create role**.

---

## Step 4: Launch the EC2 Ubuntu Server (Free Tier Eligible)

1. Search for **EC2** in the AWS Console &rarr; Click **Launch instance**.
2. **Name**: `PavePulse-Production-Server`.
3. **Application and OS Images**: Select **Ubuntu** &rarr; Choose **Ubuntu Server 22.04 LTS (HVM)** or **24.04 LTS**.
4. **Instance type**: Select **`t2.micro`** (or `t3.micro` if marked *Free tier eligible* in your region).
5. **Key pair (login)**:
   - Click **Create new key pair**.
   - Key pair name: `pavepulse-key`.
   - Key pair type: `RSA`, Private key file format: `.pem`.
   - Click **Create key pair** (a `.pem` file will download to your PC).
6. **Network settings**:
   - Check **Allow SSH traffic from** &rarr; Select **My IP** (crucial for security).
   - Check **Allow HTTP traffic from the internet** (Port 80).
   - Check **Allow HTTPS traffic from the internet** (Port 443).
7. **Configure storage**:
   - Change `8 GiB` to **`20 GiB`** gp3 (Free tier allows up to 30 GiB).
8. **Advanced details** (Scroll to bottom):
   - Under **IAM instance profile**, select: **`PavePulse-EC2-S3-Role`** (created in Step 3).
9. Click **Launch instance**.

---

## Step 5: Connect to Your EC2 Instance

Once the instance status shows **Running**:

### Option A: Using AWS Browser Connect (Simplest)
1. In the EC2 Console, select your instance and click **Connect** (top right).
2. Choose **EC2 Instance Connect** &rarr; Click **Connect**.
3. A terminal window will open in your browser directly inside the Ubuntu server!

### Option B: Using Windows PowerShell / SSH
```powershell
# In the folder where you downloaded pavepulse-key.pem:
ssh -i "pavepulse-key.pem" ubuntu@<YOUR-EC2-PUBLIC-IP>
```

---

## Step 6: Deploy PavePulse to EC2

In your EC2 Ubuntu terminal:

### 1. Clone or copy your project
```bash
cd /home/ubuntu
git clone https://github.com/<your-username>/pavepulse.git
# OR copy the project files to /home/ubuntu/pavepulse
cd pavepulse
```

### 2. Make the deployment script executable and run it:
```bash
chmod +x deploy/setup_ec2.sh
bash deploy/setup_ec2.sh
```

The script will automatically:
- Update Ubuntu system packages
- Install Python 3, pip, venv, MySQL Server, Nginx, and build tools
- Initialize the MySQL database `pavepulse_db` and user `pavepulse_user`
- Create the virtual environment and install dependencies
- Configure the systemd service `pavepulse.service` with Gunicorn
- Configure Nginx reverse proxy on port 80
- Configure the UFW firewall
- Seed default accounts (Admin, Officer, Citizen) and sample road hazards!

---

## Step 7: Connect Your S3 Bucket in `.env`

Edit the production `.env` file on EC2:
```bash
nano /home/ubuntu/pavepulse/.env
```

Update `S3_BUCKET` with your bucket name:
```ini
S3_BUCKET=pavepulse-hazards-yourname-2026
AWS_DEFAULT_REGION=ap-south-1
```
*(Leave `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` empty — boto3 automatically uses the attached EC2 IAM Role!)*

Save and exit (`Ctrl + O`, `Enter`, then `Ctrl + X`).

Restart the application service:
```bash
sudo systemctl restart pavepulse.service
```

---

## Step 8: Open and Test Your Deployed Cloud App!

In your browser, visit:
```
http://<YOUR-EC2-PUBLIC-IP>
```

### Ready-to-Use Seed Accounts:

| Role | Email | Password | What You Can Do |
| :--- | :--- | :--- | :--- |
| **Administrator** | `admin@pavepulse.org` | `Admin@123` | View all hazard statistics, review risk scores, assign maintenance officers, inspect duplicates. |
| **Maintenance Officer** | `officer@pavepulse.org` | `Officer@123` | View assigned hazards, update status to *In Progress* / *Resolved*, upload after-repair proof. |
| **Citizen** | `citizen@pavepulse.org` | `Citizen@123` | Submit road hazard complaints, drop map pins, upload damage photos, track repairs. |

---

## 🛠️ Handy EC2 Server Management Commands

```bash
# Check application status
sudo systemctl status pavepulse.service

# View live application logs
sudo journalctl -u pavepulse.service -f

# View Nginx access & error logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# Restart application after code changes
sudo systemctl restart pavepulse.service

# Restart Nginx
sudo systemctl restart nginx
```
