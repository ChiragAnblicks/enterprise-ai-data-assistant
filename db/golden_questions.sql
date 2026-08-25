-- =====================================================================
-- Golden question set - 22 questions with reference SQL.   MySQL 8
--
-- Purpose:
--   1. Regression harness. Run the natural-language question through
--      the app, compare the result with the reference SQL below.
--   2. Demo script. Questions 1, 4, 6, 12 and 19 are the best on camera.
--
-- Difficulty:  E = easy, M = medium, H = hard
-- =====================================================================


-- Q1 [E] Show total sales by month for 2026.
SELECT DATE_FORMAT(o.order_date, '%Y-%m')                                  AS month,
       ROUND(SUM(oi.quantity * oi.unit_price * (1 - oi.discount_pct/100)), 2) AS revenue
FROM orders o
JOIN order_items oi ON oi.order_id = o.order_id
WHERE o.order_status <> 'Cancelled'
  AND o.order_date >= '2026-01-01'
GROUP BY DATE_FORMAT(o.order_date, '%Y-%m')
ORDER BY month;


-- Q2 [E] List the top 10 customers by revenue.
SELECT c.customer_name,
       ROUND(SUM(oi.quantity * oi.unit_price * (1 - oi.discount_pct/100)), 2) AS revenue
FROM customers c
JOIN orders o       ON o.customer_id = c.customer_id
JOIN order_items oi ON oi.order_id   = o.order_id
WHERE o.order_status <> 'Cancelled'
GROUP BY c.customer_name
ORDER BY revenue DESC
LIMIT 10;


-- Q3 [E] Which are the top five products by quantity sold?
SELECT p.product_name, SUM(oi.quantity) AS units_sold
FROM products p
JOIN order_items oi ON oi.product_id = p.product_id
JOIN orders o       ON o.order_id    = oi.order_id
WHERE o.order_status <> 'Cancelled'
GROUP BY p.product_name
ORDER BY units_sold DESC
LIMIT 5;


-- Q4 [M] Show sales by region.
SELECT r.region_name,
       ROUND(SUM(oi.quantity * oi.unit_price * (1 - oi.discount_pct/100)), 2) AS revenue
FROM regions r
JOIN customers c    ON c.region_id   = r.region_id
JOIN orders o       ON o.customer_id = c.customer_id
JOIN order_items oi ON oi.order_id   = o.order_id
WHERE o.order_status <> 'Cancelled'
GROUP BY r.region_name
ORDER BY revenue DESC;


-- Q5 [E] How many orders are currently not shipped?
SELECT COUNT(*) AS unshipped_orders
FROM orders
WHERE shipped_date IS NULL
  AND order_status <> 'Cancelled';


-- Q6 [M] Revenue by product category with the number of orders.
SELECT cat.category_name,
       COUNT(DISTINCT o.order_id) AS order_count,
       ROUND(SUM(oi.quantity * oi.unit_price * (1 - oi.discount_pct/100)), 2) AS revenue
FROM categories cat
JOIN products p     ON p.category_id = cat.category_id
JOIN order_items oi ON oi.product_id = p.product_id
JOIN orders o       ON o.order_id    = oi.order_id
WHERE o.order_status <> 'Cancelled'
GROUP BY cat.category_name
ORDER BY revenue DESC;


-- Q7 [M] Which customers have never placed an order?
SELECT c.customer_id, c.customer_name, c.segment
FROM customers c
LEFT JOIN orders o ON o.customer_id = c.customer_id
WHERE o.order_id IS NULL
ORDER BY c.customer_name;


-- Q8 [M] Average discount percentage by customer segment.
SELECT c.segment,
       ROUND(AVG(oi.discount_pct), 2) AS avg_discount_pct,
       MAX(oi.discount_pct)           AS max_discount_pct
FROM customers c
JOIN orders o       ON o.customer_id = c.customer_id
JOIN order_items oi ON oi.order_id   = o.order_id
GROUP BY c.segment
ORDER BY avg_discount_pct DESC;


-- Q9 [M] Show the sales performance of each employee with their manager name.
SELECT CONCAT(e.first_name, ' ', e.last_name)  AS employee,
       CONCAT(m.first_name, ' ', m.last_name)  AS manager,
       COUNT(DISTINCT o.order_id)              AS orders,
       ROUND(SUM(oi.quantity * oi.unit_price * (1 - oi.discount_pct/100)), 2) AS revenue
FROM employees e
LEFT JOIN employees m ON m.employee_id = e.manager_id
JOIN orders o         ON o.employee_id = e.employee_id
JOIN order_items oi   ON oi.order_id   = o.order_id
WHERE o.order_status <> 'Cancelled'
GROUP BY employee, manager
ORDER BY revenue DESC;


-- Q10 [E] Which products need reordering?
SELECT product_name, units_in_stock, reorder_level
FROM products
WHERE units_in_stock < reorder_level
  AND discontinued = 0
ORDER BY units_in_stock;


-- Q11 [M] What is the average order value?
SELECT ROUND(AVG(order_total), 2) AS avg_order_value
FROM (
    SELECT o.order_id,
           SUM(oi.quantity * oi.unit_price * (1 - oi.discount_pct/100)) AS order_total
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.order_id
    WHERE o.order_status <> 'Cancelled'
    GROUP BY o.order_id
) t;


-- Q12 [H] Show monthly revenue for the last 12 months with the running total.
WITH monthly AS (
    SELECT DATE_FORMAT(o.order_date, '%Y-%m') AS mth,
           SUM(oi.quantity * oi.unit_price * (1 - oi.discount_pct/100)) AS revenue
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.order_id
    WHERE o.order_status <> 'Cancelled'
      AND o.order_date >= DATE_SUB('2026-07-01', INTERVAL 11 MONTH)
    GROUP BY DATE_FORMAT(o.order_date, '%Y-%m')
)
SELECT mth AS month,
       ROUND(revenue, 2)                              AS revenue,
       ROUND(SUM(revenue) OVER (ORDER BY mth), 2)     AS running_total
FROM monthly
ORDER BY mth;


-- Q13 [H] Top 3 products by revenue within each category.
WITH ranked AS (
    SELECT cat.category_name,
           p.product_name,
           SUM(oi.quantity * oi.unit_price * (1 - oi.discount_pct/100)) AS revenue,
           ROW_NUMBER() OVER (PARTITION BY cat.category_name
                              ORDER BY SUM(oi.quantity * oi.unit_price
                                           * (1 - oi.discount_pct/100)) DESC) AS rn
    FROM categories cat
    JOIN products p     ON p.category_id = cat.category_id
    JOIN order_items oi ON oi.product_id = p.product_id
    JOIN orders o       ON o.order_id    = oi.order_id
    WHERE o.order_status <> 'Cancelled'
    GROUP BY cat.category_name, p.product_name
)
SELECT category_name, product_name, ROUND(revenue, 2) AS revenue
FROM ranked
WHERE rn <= 3
ORDER BY category_name, revenue DESC;


-- Q14 [M] How many returns were there by reason, and what did they cost us?
SELECT reason_code,
       COUNT(*)                    AS return_count,
       ROUND(SUM(refund_amount), 2) AS total_refunded
FROM product_returns
WHERE return_status = 'Approved'
GROUP BY reason_code
ORDER BY total_refunded DESC;


-- Q15 [H] Net revenue by category after deducting refunds.
WITH gross AS (
    SELECT p.category_id,
           SUM(oi.quantity * oi.unit_price * (1 - oi.discount_pct/100)) AS revenue
    FROM order_items oi
    JOIN orders o   ON o.order_id   = oi.order_id
    JOIN products p ON p.product_id = oi.product_id
    WHERE o.order_status <> 'Cancelled'
    GROUP BY p.category_id
),
refunds AS (
    SELECT p.category_id, SUM(pr.refund_amount) AS refunded
    FROM product_returns pr
    JOIN products p ON p.product_id = pr.product_id
    WHERE pr.return_status = 'Approved'
    GROUP BY p.category_id
)
SELECT cat.category_name,
       ROUND(g.revenue, 2)                              AS gross_revenue,
       ROUND(COALESCE(rf.refunded, 0), 2)               AS refunds,
       ROUND(g.revenue - COALESCE(rf.refunded, 0), 2)   AS net_revenue
FROM gross g
JOIN categories cat  ON cat.category_id = g.category_id
LEFT JOIN refunds rf ON rf.category_id  = g.category_id
ORDER BY net_revenue DESC;


-- Q16 [M] Which orders were delivered later than the required date?
SELECT o.order_id, c.customer_name, o.required_date, o.shipped_date,
       DATEDIFF(o.shipped_date, o.required_date) AS days_late
FROM orders o
JOIN customers c ON c.customer_id = o.customer_id
WHERE o.shipped_date > o.required_date
ORDER BY days_late DESC
LIMIT 20;


-- Q17 [M] Payment collection summary by payment method.
SELECT payment_method,
       COUNT(*)              AS payment_count,
       ROUND(SUM(amount), 2) AS total_collected
FROM payments
WHERE payment_status = 'Cleared'
GROUP BY payment_method
ORDER BY total_collected DESC;


-- Q18 [H] Customers whose total revenue exceeds their credit limit.
SELECT c.customer_name, c.segment, c.credit_limit,
       ROUND(SUM(oi.quantity * oi.unit_price * (1 - oi.discount_pct/100)), 2) AS revenue
FROM customers c
JOIN orders o       ON o.customer_id = c.customer_id
JOIN order_items oi ON oi.order_id   = o.order_id
WHERE o.order_status <> 'Cancelled'
GROUP BY c.customer_name, c.segment, c.credit_limit
HAVING revenue > c.credit_limit
ORDER BY revenue DESC;


-- Q19 [M] Compare this year's revenue with last year's, by quarter.
SELECT YEAR(o.order_date)    AS yr,
       QUARTER(o.order_date) AS qtr,
       ROUND(SUM(oi.quantity * oi.unit_price * (1 - oi.discount_pct/100)), 2) AS revenue
FROM orders o
JOIN order_items oi ON oi.order_id = o.order_id
WHERE o.order_status <> 'Cancelled'
  AND o.order_date >= '2025-01-01'
GROUP BY YEAR(o.order_date), QUARTER(o.order_date)
ORDER BY yr, qtr;


-- Q20 [M] Which suppliers do we buy the most from, by product revenue?
SELECT s.supplier_name, s.country,
       COUNT(DISTINCT p.product_id) AS products_sold,
       ROUND(SUM(oi.quantity * oi.unit_price * (1 - oi.discount_pct/100)), 2) AS revenue
FROM suppliers s
JOIN products p     ON p.supplier_id = s.supplier_id
JOIN order_items oi ON oi.product_id = p.product_id
JOIN orders o       ON o.order_id    = oi.order_id
WHERE o.order_status <> 'Cancelled'
GROUP BY s.supplier_name, s.country
ORDER BY revenue DESC;


-- Q21 [M] Show cancelled orders by month in 2026.
SELECT DATE_FORMAT(order_date, '%Y-%m') AS month, COUNT(*) AS cancelled_orders
FROM orders
WHERE order_status = 'Cancelled'
  AND order_date >= '2026-01-01'
GROUP BY DATE_FORMAT(order_date, '%Y-%m')
ORDER BY month;


-- Q22 [H] Average days from order to shipment, by shipper.
SELECT sh.shipper_name,
       COUNT(*)                                              AS shipments,
       ROUND(AVG(DATEDIFF(o.shipped_date, o.order_date)), 1) AS avg_days_to_ship
FROM orders o
JOIN shippers sh ON sh.shipper_id = o.shipper_id
WHERE o.shipped_date IS NOT NULL
GROUP BY sh.shipper_name
ORDER BY avg_days_to_ship;


-- =====================================================================
-- Cross-module questions. These need BOTH the database and the uploaded
-- documents, and they are the strongest thing to show in the demo.
--
-- Q23  "What is our return policy, and how many returns did we actually
--        have last quarter?"        -> ReturnPolicy.txt + Q14
-- Q24  "What warranty do we offer on networking products?"
--                                    -> WarrantyTerms.docx + categories
-- Q25  "What discount is an Enterprise customer allowed, and are we
--        staying within it?"        -> SalesPolicy.pdf + Q8
--
-- Q26 is a deliberate negative test - the documents do not cover it.
-- The assistant must say so instead of inventing an answer.
-- Q26  "What is the company's parental leave policy?"
-- =====================================================================
