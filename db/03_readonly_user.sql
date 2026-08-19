-- =====================================================================
-- Read-only application user for the AI Data Assistant  (MySQL 8)
-- Run as root, or any user holding GRANT OPTION.
--
-- This is the PRIMARY guardrail for "SELECT statements only".
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1. The user and its privileges
-- ---------------------------------------------------------------------
--Login with root user first
DROP USER IF EXISTS 'capstone_ro'@'localhost';

CREATE USER 'capstone_ro'@'localhost'
    IDENTIFIED BY 'capstone_ro@123'
    WITH MAX_USER_CONNECTIONS 5
         MAX_QUERIES_PER_HOUR 5000;

-- SELECT and nothing else. No INSERT, UPDATE, DELETE, CREATE, DROP,
-- ALTER, FILE, PROCESS, or EXECUTE.
GRANT SELECT ON CapstoneCore.* TO 'capstone_ro'@'localhost';

FLUSH PRIVILEGES;

-- If the PHP backend connects over TCP from another host, create the
-- account for that host instead of localhost, e.g.
--   CREATE USER 'capstone_ro'@'127.0.0.1' IDENTIFIED BY '...';
--   GRANT SELECT ON CapstoneCore.* TO 'capstone_ro'@'127.0.0.1';


-- ---------------------------------------------------------------------
-- 2. Verification - run these AS capstone_ro and screenshot the output
--
--   mysql -u capstone_ro -p CapstoneCore
--
--   SELECT COUNT(*) FROM orders;
--       -> works
--   DELETE FROM orders WHERE order_id = 10001;
--       -> ERROR 1142 (42000): DELETE command denied to user
--          'capstone_ro'@'localhost' for table 'orders'
--   CREATE TABLE t (x INT);
--       -> ERROR 1142 (42000): CREATE command denied to user
--   UPDATE products SET unit_price = 0;
--       -> ERROR 1142 (42000): UPDATE command denied to user
--   LOAD DATA INFILE '/etc/passwd' INTO TABLE t;
--       -> ERROR 1045 / 1142: no FILE privilege
-- ---------------------------------------------------------------------


-- ---------------------------------------------------------------------
-- 3. Session settings the PHP backend MUST apply after connecting
--
-- MySQL cannot attach these to the account, so the application does it.
-- Put this in your PDO wrapper, immediately after the connection opens:
--
--   $pdo = new PDO($dsn, $user, $pass, [
--       PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION,
--       PDO::ATTR_EMULATE_PREPARES   => false,   // blocks stacked queries
--       PDO::MYSQL_ATTR_MULTI_STATEMENTS => false,
--       PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
--   ]);
--   $pdo->exec("SET SESSION transaction_read_only = ON");
--   $pdo->exec("SET SESSION max_execution_time = 10000");   -- 10 seconds
--   $pdo->exec("SET SESSION sql_mode = 'STRICT_ALL_TABLES'");
--
-- PDO::MYSQL_ATTR_MULTI_STATEMENTS => false is the important one. With
-- multi-statement enabled, a single execute() can run
--   SELECT 1; DROP TABLE orders;
-- Turning it off, plus the SELECT-only grant above, closes that door
-- twice over.
--
-- max_execution_time applies to SELECT statements only, which is exactly
-- what this application runs. It is expressed in milliseconds.
-- ---------------------------------------------------------------------


-- ---------------------------------------------------------------------
-- 4. Optional: verify the grant from SQL
--
--   SHOW GRANTS FOR 'capstone_ro'@'localhost';
--
-- Expected output, and nothing more:
--   GRANT USAGE ON *.* TO `capstone_ro`@`localhost`
--   GRANT SELECT ON `CapstoneCore`.* TO `capstone_ro`@`localhost`
-- ---------------------------------------------------------------------
