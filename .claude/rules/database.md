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

- `ratings.score`: 1 = thumbs up, 0 = thumbs down
- Unique constraint on `(station, ip)` prevents duplicate votes
- `users.token`: auth token set on login, used for Bearer auth
- `feedback`: stores message + full user profile snapshot (minus password)
- Credentials loaded from environment variables via python-dotenv (`api/.env.example`)