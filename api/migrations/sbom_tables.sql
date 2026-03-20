-- SBOM History Tables
-- Run once against the radiocalico database to enable --save-db in generate_sbom.py.
-- Compatible with MySQL 5.7+ and MySQL 8.0 (Docker).
--
-- Usage:
--   mysql -u root -p radiocalico < api/migrations/sbom_tables.sql

-- One row per scan run
CREATE TABLE IF NOT EXISTS sbom_scans (
  id INT AUTO_INCREMENT PRIMARY KEY,
  project VARCHAR(100) NOT NULL,
  scan_date DATE NOT NULL,
  total_packages INT DEFAULT 0,
  total_vulns INT DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_project_date (project, scan_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- One row per package per scan
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- One row per vulnerability per scan
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- One row per impact analysis per vulnerability per scan
CREATE TABLE IF NOT EXISTS sbom_impact_analysis (
  id INT AUTO_INCREMENT PRIMARY KEY,
  scan_id INT NOT NULL,
  vuln_id VARCHAR(100) NOT NULL,
  package_name VARCHAR(255) NOT NULL,
  rating VARCHAR(50) NOT NULL,
  analysis TEXT NOT NULL,
  FOREIGN KEY (scan_id) REFERENCES sbom_scans(id) ON DELETE CASCADE,
  UNIQUE KEY unique_scan_vuln (scan_id, vuln_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;