DROP DATABASE IF EXISTS genscene_sample;
CREATE DATABASE genscene_sample;
USE genscene_sample;

DROP USER IF EXISTS 'genscene_sample_usr'@'%';
CREATE USER 'genscene_sample_usr'@'%' IDENTIFIED BY 'usr_genscene_sample';
GRANT ALL on *.* TO 'genscene_sample_usr'@'%';
FLUSH PRIVILEGES;

CREATE TABLE people (
    id INT AUTO_INCREMENT PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    height DECIMAL(5,2),  -- Height in meters, allowing for 3 digits before the decimal and 2 digits after
    date_of_birth DATE,
    email VARCHAR(100) UNIQUE,
    gender ENUM('Male', 'Female', 'Other'),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO people (first_name, last_name, height, date_of_birth, email, gender) VALUES
('John', 'Doe', 1.75, '1990-01-15', 'john.doe@example.com', 'Male'),
('Jane', 'Smith', 1.62, '1985-03-22', 'jane.smith@example.com', 'Female'),
('Alice', 'Johnson', 1.68, '1992-07-10', 'alice.johnson@example.com', 'Female'),
('Bob', 'Brown', 1.80, '1988-05-30', 'bob.brown@example.com', 'Male'),
('Charlie', 'Davis', 1.77, '1991-11-08', 'charlie.davis@example.com', 'Male'),
('Eve', 'Miller', 1.55, '1995-09-12', 'eve.miller@example.com', 'Female'),
('Frank', 'Wilson', 1.85, '1982-06-18', 'frank.wilson@example.com', 'Male'),
('Grace', 'Moore', 1.70, '1993-02-25', 'grace.moore@example.com', 'Female'),
('Hank', 'Taylor', 1.73, '1994-08-14', 'hank.taylor@example.com', 'Male'),
('Ivy', 'Anderson', 1.60, '1996-12-05', 'ivy.anderson@example.com', 'Female'),
('Jack', 'Thomas', 1.78, '1990-04-16', 'jack.thomas@example.com', 'Male'),
('Karen', 'Jackson', 1.65, '1987-10-23', 'karen.jackson@example.com', 'Female'),
('Leo', 'White', 1.83, '1992-01-29', 'leo.white@example.com', 'Male'),
('Mia', 'Harris', 1.58, '1991-07-20', 'mia.harris@example.com', 'Female'),
('Nick', 'Martin', 1.72, '1989-03-04', 'nick.martin@example.com', 'Male'),
('Olivia', 'Garcia', 1.67, '1993-05-18', 'olivia.garcia@example.com', 'Female'),
('Paul', 'Martinez', 1.74, '1986-11-12', 'paul.martinez@example.com', 'Male'),
('Quinn', 'Robinson', 1.69, '1990-02-07', 'quinn.robinson@example.com', 'Other'),
('Rachel', 'Clark', 1.63, '1994-09-26', 'rachel.clark@example.com', 'Female'),
('Steve', 'Lewis', 1.82, '1985-08-03', 'steve.lewis@example.com', 'Male');
