# Database Schema

MySQL 5.7 (local/Homebrew) or MySQL 8.0 (Docker).

```sql
CREATE TABLE ratings (
  id INT AUTO_INCREMENT PRIMARY KEY,
  station VARCHAR(255) NOT NULL,
  score TINYINT NOT NULL,
  ip VARCHAR(45) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY unique_rating (station, ip)
);

CREATE TABLE users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(50) NOT NULL UNIQUE,
  password_hash VARCHAR(64) NOT NULL,
  salt VARCHAR(32) NOT NULL,
  token VARCHAR(64) DEFAULT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE profiles (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL UNIQUE,
  nickname VARCHAR(100) DEFAULT '',
  email VARCHAR(255) DEFAULT '',
  genres VARCHAR(500) DEFAULT '',
  about TEXT,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE feedback (
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
```

## SBOM History Tables

Created by `api/migrations/sbom_tables.sql`. Used by `scripts/generate_sbom.py --save-db` for historical tracking.

```sql
CREATE TABLE IF NOT EXISTS sbom_scans (
  id INT AUTO_INCREMENT PRIMARY KEY,
  project VARCHAR(100) NOT NULL,
  scan_date DATE NOT NULL,
  total_packages INT DEFAULT 0,
  total_vulns INT DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_project_date (project, scan_date)
);

CREATE TABLE IF NOT EXISTS sbom_packages (
  id INT AUTO_INCREMENT PRIMARY KEY,
  scan_id INT NOT NULL,
  ecosystem ENUM('python','nodejs','dotnet','maven','gradle') NOT NULL,
  name VARCHAR(255) NOT NULL,
  version VARCHAR(100) NOT NULL,
  license VARCHAR(255) DEFAULT '',
  latest_version VARCHAR(100) DEFAULT '',
  FOREIGN KEY (scan_id) REFERENCES sbom_scans(id) ON DELETE CASCADE,
  INDEX idx_scan_eco (scan_id, ecosystem)
);

CREATE TABLE IF NOT EXISTS sbom_vulnerabilities (
  id INT AUTO_INCREMENT PRIMARY KEY,
  scan_id INT NOT NULL,
  package_name VARCHAR(255) NOT NULL,
  ecosystem ENUM('python','nodejs','dotnet','maven','gradle') NOT NULL,
  vuln_id VARCHAR(100) NOT NULL,
  severity VARCHAR(20) DEFAULT '',
  cvss_score DECIMAL(3,1) DEFAULT NULL,
  cvss_vector VARCHAR(255) DEFAULT '',
  published_date DATE DEFAULT NULL,
  modified_date DATE DEFAULT NULL,
  fix_version VARCHAR(100) DEFAULT '',
  reference_url VARCHAR(500) DEFAULT '',
  description VARCHAR(500) DEFAULT '',
  FOREIGN KEY (scan_id) REFERENCES sbom_scans(id) ON DELETE CASCADE,
  INDEX idx_scan_vuln (scan_id, vuln_id)
);

CREATE TABLE IF NOT EXISTS sbom_impact_analysis (
  id INT AUTO_INCREMENT PRIMARY KEY,
  scan_id INT NOT NULL,
  vuln_id VARCHAR(100) NOT NULL,
  package_name VARCHAR(255) NOT NULL,
  rating VARCHAR(50) NOT NULL,
  analysis TEXT NOT NULL,
  FOREIGN KEY (scan_id) REFERENCES sbom_scans(id) ON DELETE CASCADE,
  UNIQUE KEY unique_scan_vuln (scan_id, vuln_id)
);
```

- `sbom_scans`: one row per scan run, tracks project name, date, and totals
- `sbom_packages`: one row per package per scan, with ecosystem, version, license, and latest version
- `sbom_vulnerabilities`: one row per vulnerability per scan, with CVSS scores, dates, and references
- `sbom_impact_analysis`: one row per impact assessment per vulnerability, with rating and analysis text
- All SBOM tables cascade-delete from `sbom_scans` — deleting a scan removes all related rows

- `ratings.score`: 1 = thumbs up, 0 = thumbs down
- Unique constraint on `(station, ip)` prevents duplicate votes
- `users.token`: auth token set on login, used for Bearer auth
- `feedback`: stores message + full user profile snapshot (minus password)
- Credentials loaded from environment variables via python-dotenv (`api/.env.example`)