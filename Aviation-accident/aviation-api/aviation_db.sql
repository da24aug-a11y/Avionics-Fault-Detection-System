CREATE DATABASE IF NOT EXISTS aviation_db;
USE aviation_db;

CREATE TABLE IF NOT EXISTS incidents (
    id INT AUTO_INCREMENT PRIMARY KEY,
    time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    input_text TEXT,
    prediction_label VARCHAR(225),
    severity VARCHAR(50),
    risk_score FLOAT,
    is_correct INT DEFAULT 1
);