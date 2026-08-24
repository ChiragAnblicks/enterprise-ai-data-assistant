-- =====================================================================
-- Generates docs/schema_context.md straight from the MySQL catalog.
-- This markdown is injected into every NL-to-SQL prompt, so it must
-- always match the live database. Regenerate it after any DDL change.
--
-- Usage (the -N -B --raw flags strip headers, borders and escaping):
--   mysql -u root -p -N -B --raw CapstoneCore \
--         < 04_generate_schema_context.sql > ../docs/schema_context.md
--
-- Business meaning comes from the COMMENT clauses in 01_schema.sql, so
-- edit those and regenerate rather than hand-editing the markdown.
-- =====================================================================

SELECT line FROM (

    SELECT 0 AS grp, '' AS tbl, 0 AS ord,
           '# Database Schema Context' AS line
    UNION ALL SELECT 0, '', 1, ''
    UNION ALL SELECT 0, '', 2,
        'Database: CapstoneCore (MySQL 8). All identifiers are lowercase.'
    UNION ALL SELECT 0, '', 3, ''

    -- one heading per table
    UNION ALL
    SELECT 1, t.TABLE_NAME, 0,
           CONCAT('## ', t.TABLE_NAME,
                  IF(t.TABLE_COMMENT = '' OR t.TABLE_COMMENT IS NULL,
                     '', CONCAT(' - ', t.TABLE_COMMENT)))
    FROM information_schema.TABLES t
    WHERE t.TABLE_SCHEMA = DATABASE()
      AND t.TABLE_TYPE   = 'BASE TABLE'

    -- one bullet per column
    UNION ALL
    SELECT 1, c.TABLE_NAME, c.ORDINAL_POSITION,
           CONCAT('- ', c.COLUMN_NAME,
                  ' (', c.COLUMN_TYPE, ')',
                  IF(c.COLUMN_KEY = 'PRI', ' PK', ''),
                  IFNULL(CONCAT(' FK -> ', k.REFERENCED_TABLE_NAME,
                                '.', k.REFERENCED_COLUMN_NAME), ''),
                  IF(c.COLUMN_COMMENT = '' OR c.COLUMN_COMMENT IS NULL,
                     '', CONCAT(' -- ', c.COLUMN_COMMENT)))
    FROM information_schema.COLUMNS c
    LEFT JOIN information_schema.KEY_COLUMN_USAGE k
           ON  k.TABLE_SCHEMA = c.TABLE_SCHEMA
           AND k.TABLE_NAME   = c.TABLE_NAME
           AND k.COLUMN_NAME  = c.COLUMN_NAME
           AND k.REFERENCED_TABLE_NAME IS NOT NULL
    WHERE c.TABLE_SCHEMA = DATABASE()

    -- blank line after each table block
    UNION ALL
    SELECT 1, t.TABLE_NAME, 999, ''
    FROM information_schema.TABLES t
    WHERE t.TABLE_SCHEMA = DATABASE()
      AND t.TABLE_TYPE   = 'BASE TABLE'

) x
ORDER BY grp, tbl, ord;
