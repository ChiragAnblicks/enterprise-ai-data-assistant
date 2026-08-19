
-- Create database
CREATE DATABASE CapstoneCore

-- Create the user
CREATE USER 'capstonecore_owner'@'%' IDENTIFIED BY 'Capstone@123';

-- Grant full privileges on this database only
GRANT ALL PRIVILEGES ON CapstoneCore.* TO 'capstonecore_owner'@'%';

-- Apply the changes
FLUSH PRIVILEGES;

-- To allow user for user management for this database
GRANT GRANT OPTION ON CapstoneCore.* TO 'capstonecore_owner'@'%';

-- Login to database
-- mysql -u capstonecore_owner -p
-- mysql -u capstonecore_owner -p CapstoneCore
