-- PavePulse MySQL Database Initialization Script
-- Run this on your EC2 MySQL server:
-- sudo mysql -u root < deploy/mysql_setup.sql

CREATE DATABASE IF NOT EXISTS pavepulse_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Create dedicated application user
CREATE USER IF NOT EXISTS 'pavepulse_user'@'localhost' IDENTIFIED BY 'StrongPavePulse2026!';

-- Grant required privileges
GRANT ALL PRIVILEGES ON pavepulse_db.* TO 'pavepulse_user'@'localhost';
FLUSH PRIVILEGES;

-- Verify
SELECT User, Host FROM mysql.user WHERE User='pavepulse_user';
