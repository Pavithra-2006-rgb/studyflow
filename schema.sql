-- StudyFlow 2.0 MySQL Schema
-- Run this once: mysql -u root -p < schema.sql

CREATE DATABASE IF NOT EXISTS studyflow CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE studyflow;

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    username     VARCHAR(50)  UNIQUE NOT NULL,
    full_name    VARCHAR(100) NOT NULL,
    password     VARCHAR(255) NOT NULL,   -- SHA256 hashed
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Saved schedules per user (one active schedule per user)
CREATE TABLE IF NOT EXISTS schedules (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    user_id      INT NOT NULL,
    schedule_json LONGTEXT NOT NULL,       -- full schedule JSON blob
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at   DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY uq_user (user_id)           -- one schedule per user, upsert on save
);

-- Task completion tracking per user
CREATE TABLE IF NOT EXISTS completions (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    user_id      INT NOT NULL,
    date_str     VARCHAR(10) NOT NULL,     -- YYYY-MM-DD
    subject      VARCHAR(200) NOT NULL,
    completed    TINYINT(1) DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY uq_task (user_id, date_str, subject)
);

-- Demo user (password = 'study123')
INSERT IGNORE INTO users (username, full_name, password)
VALUES ('student', 'Student User', SHA2('study123', 256));

INSERT IGNORE INTO users (username, full_name, password)
VALUES ('admin', 'Admin User', SHA2('admin123', 256));
