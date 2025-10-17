
-- Kreiraj bazu ako ne postoji
CREATE DATABASE IF NOT EXISTS korisnici
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;

USE korisnici;

-- Kreiraj tabelu users ako ne postoji
CREATE TABLE IF NOT EXISTS users (
  idUser   INT AUTO_INCREMENT PRIMARY KEY,
  email    VARCHAR(256) NOT NULL UNIQUE,
  password VARCHAR(256) NOT NULL,
  forename VARCHAR(256) NOT NULL,
  surname  VARCHAR(256) NOT NULL,
  role     ENUM('owner','customer','courier') NOT NULL
) ENGINE=InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_0900_ai_ci;

-- Ubaci owner korisnika ako već ne postoji
INSERT INTO users (email, password, forename, surname, role)
SELECT 'onlymoney@gmail.com', 'evenmoremoney', 'Scrooge', 'McDuck', 'owner'
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM users WHERE email = 'onlymoney@gmail.com'
);