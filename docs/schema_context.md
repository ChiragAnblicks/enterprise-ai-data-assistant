# Database Schema Context

Database: CapstoneCore (MySQL 8). All identifiers are lowercase and unquoted.

## Business rules the model must follow

- Line revenue = `oi.quantity * oi.unit_price * (1 - oi.discount_pct / 100)`.
- `orders.freight` is a header-level delivery charge. Do NOT add it to line revenue
  unless the question explicitly asks about freight or total invoice value.
- Exclude cancelled orders from every revenue figure: `o.order_status <> 'Cancelled'`.
- "Sales", "revenue" and "turnover" all mean line revenue as defined above.
- "Customer" means a company in `customers`, not a contact person.
- Refunds live in `product_returns.refund_amount`. Net revenue = revenue - refunds.
- `payments.amount` is cash received and may be partial; it is not revenue.
- A product is currently sellable when `products.discontinued = 0`.
- Warranty length comes from `categories.warranty_months`, not from `products`.

## MySQL dialect rules

- Month bucket: `DATE_FORMAT(o.order_date, '%Y-%m')`. There is no TO_CHAR.
- Rounding money: `ROUND(SUM(...), 2)`. No type cast is needed.
- String concatenation: `CONCAT(a, ' ', b)`. Never use `||` - in MySQL that is
  the OR operator, not concatenation.
- Date difference in days: `DATEDIFF(o.shipped_date, o.required_date)`.
  Subtracting two DATE values does NOT give days in MySQL.
- Date parts: `YEAR(o.order_date)`, `QUARTER(o.order_date)`, `MONTH(o.order_date)`.
- Relative dates: `o.order_date >= DATE_SUB(CURDATE(), INTERVAL 12 MONTH)`.
- Month truncation: `DATE_FORMAT(o.order_date, '%Y-%m-01')`. There is no DATE_TRUNC.
- Booleans are TINYINT(1). Compare with `= 1` and `= 0`, not TRUE/FALSE.
- Text comparison is already case-insensitive under the utf8mb4_0900_ai_ci
  collation, so plain `LIKE` is enough. There is no ILIKE.
- `ONLY_FULL_GROUP_BY` is enabled by default: every selected column that is not
  inside an aggregate must appear in the GROUP BY clause.
- Division guard: `SUM(a) / NULLIF(SUM(b), 0)`.
- Row limiting: `LIMIT 10`. There is no FETCH FIRST.
- CTEs (`WITH`) and window functions are supported from MySQL 8.0.
- Always use explicit `JOIN ... ON` with short table aliases.

## Join map

- orders.customer_id -> customers.customer_id
- orders.employee_id -> employees.employee_id
- orders.shipper_id -> shippers.shipper_id
- order_items.order_id -> orders.order_id
- order_items.product_id -> products.product_id
- products.category_id -> categories.category_id
- products.supplier_id -> suppliers.supplier_id
- customers.region_id -> regions.region_id
- employees.region_id -> regions.region_id
- employees.manager_id -> employees.employee_id (self join)
- payments.order_id -> orders.order_id
- product_returns.order_id -> orders.order_id
- product_returns.product_id -> products.product_id

## Tables

## categories - Product categories. warranty_months is the standard warranty for the category.
- category_id (int) PK
- category_name (varchar(60))
- description (varchar(200))
- warranty_months (int) -- Standard warranty in months for this category.

## customers - Companies that place orders. segment drives the discount and payment terms.
- customer_id (int) PK
- customer_name (varchar(100))
- contact_name (varchar(80))
- segment (varchar(20)) -- Enterprise, Mid-Market, SMB, Government or Education.
- city (varchar(60))
- state_province (varchar(60))
- country (varchar(60))
- region_id (int) FK -> regions.region_id
- credit_limit (decimal(12,2)) -- Maximum outstanding balance allowed for the customer.
- signup_date (date)
- is_active (tinyint(1))

## employees - Sales staff. manager_id is a self reference to the reporting manager.
- employee_id (int) PK
- first_name (varchar(50))
- last_name (varchar(50))
- job_title (varchar(60))
- email (varchar(120))
- hire_date (date)
- manager_id (int) FK -> employees.employee_id -- Self reference to the reporting manager.
- region_id (int) FK -> regions.region_id

## order_items - Order line detail. Revenue per line = quantity * unit_price * (1 - discount_pct/100).
- order_id (int) PK FK -> orders.order_id
- line_no (int) PK
- product_id (int) FK -> products.product_id
- quantity (int)
- unit_price (decimal(10,2)) -- Price at the time of sale. May differ from products.unit_price.
- discount_pct (decimal(5,2)) -- Line discount percentage, 0 to 20.

## orders - Order header. One row per customer order. Cancelled orders have no payment.
- order_id (int) PK
- customer_id (int) FK -> customers.customer_id
- employee_id (int) FK -> employees.employee_id
- shipper_id (int) FK -> shippers.shipper_id
- order_date (date)
- required_date (date)
- shipped_date (date) -- NULL when not shipped yet or cancelled.
- order_status (varchar(20)) -- Completed, Shipped, Processing or Cancelled.
- ship_city (varchar(60))
- ship_country (varchar(60))
- freight (decimal(10,2)) -- Delivery charge on the order header, not part of line revenue.

## payments - Customer payments received against an order.
- payment_id (int) PK
- order_id (int) FK -> orders.order_id
- payment_date (date)
- amount (decimal(12,2))
- payment_method (varchar(30))
- payment_status (varchar(20))

## product_returns - Goods returned by customers with reason and refund value.
- return_id (int) PK
- order_id (int) FK -> orders.order_id
- product_id (int) FK -> products.product_id
- return_date (date)
- quantity (int)
- reason_code (varchar(30)) -- DAMAGED, WRONG_ITEM, NOT_AS_DESCRIBED, LATE_DELIVERY or CHANGED_MIND.
- refund_amount (decimal(12,2))
- return_status (varchar(20))

## products - Sellable items. unit_price is the current list price.
- product_id (int) PK
- product_name (varchar(120))
- category_id (int) FK -> categories.category_id
- supplier_id (int) FK -> suppliers.supplier_id
- unit_price (decimal(10,2)) -- Current list price.
- units_in_stock (int)
- reorder_level (int)
- discontinued (tinyint(1)) -- 1 means the product is no longer sold.

## regions - Sales regions used to group customers and employees.
- region_id (int) PK
- region_name (varchar(50))
- region_head (varchar(80))

## shippers - Logistics partners that deliver orders.
- shipper_id (int) PK
- shipper_name (varchar(60))
- phone (varchar(30))

## suppliers - Vendors that supply products.
- supplier_id (int) PK
- supplier_name (varchar(100))
- contact_name (varchar(80))
- city (varchar(60))
- country (varchar(60))
- phone (varchar(30))
- email (varchar(120))

