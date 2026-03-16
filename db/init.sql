-- Radio Calico database schema
-- Auto-executed on first Docker MySQL container startup
-- Note: MYSQL_USER/MYSQL_PASSWORD env vars in docker-compose create the user
-- and grant all privileges on MYSQL_DATABASE automatically.

CREATE TABLE IF NOT EXISTS ratings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    station VARCHAR(255) NOT NULL,
    score TINYINT NOT NULL,
    ip VARCHAR(45) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_rating (station, ip)
);

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(64) NOT NULL,
    salt VARCHAR(32) NOT NULL,
    token VARCHAR(64) DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS profiles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL UNIQUE,
    nickname VARCHAR(100) DEFAULT '',
    email VARCHAR(255) DEFAULT '',
    genres VARCHAR(500) DEFAULT '',
    about TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS feedback (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) DEFAULT '',
    message TEXT NOT NULL,
    ip VARCHAR(45) DEFAULT '',
    username VARCHAR(50) DEFAULT '',
    nickname VARCHAR(100) DEFAULT '',
    genres VARCHAR(500) DEFAULT '',
    about TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
