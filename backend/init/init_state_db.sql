DROP DATABASE IF EXISTS genscene_state;
CREATE DATABASE genscene_state;
USE genscene_state;

DROP USER IF EXISTS 'genscene_state_usr'@'%';
CREATE USER 'genscene_state_usr'@'%' IDENTIFIED BY 'usr_state_genscene';
GRANT ALL on *.* TO 'genscene_state_usr'@'%';
FLUSH PRIVILEGES;
