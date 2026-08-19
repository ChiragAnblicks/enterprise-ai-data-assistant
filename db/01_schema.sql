-- =====================================================================
-- Enterprise AI Data Assistant - Sample Database Schema
-- Target: MySQL 8.0.16 or later (CHECK constraints are enforced from
--         8.0.16; on earlier versions they are parsed and ignored)
-- Database: CapstoneCore
--
-- Run order: 01_schema.sql -> 02_seed_data.sql -> 03_readonly_user.sql
--
-- Create the database first:
--   CREATE DATABASE CapstoneCore
--     CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
--   USE CapstoneCore;
--
-- NOTE: MySQL silently IGNORES column-level REFERENCES clauses, so every
--       foreign key below is declared as a table-level constraint.
--       This is the single most common porting mistake from PostgreSQL.
-- =====================================================================

SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS product_returns;
DROP TABLE IF EXISTS payments;
DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS suppliers;
DROP TABLE IF EXISTS categories;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS employees;
DROP TABLE IF EXISTS shippers;
DROP TABLE IF EXISTS regions;
SET FOREIGN_KEY_CHECKS = 1;

-- ---------------------------------------------------------------------
-- Reference / master tables
-- ---------------------------------------------------------------------
CREATE TABLE regions (
    region_id    INT          NOT NULL,
    region_name  VARCHAR(50)  NOT NULL,
    region_head  VARCHAR(80),
    PRIMARY KEY (region_id),
    UNIQUE KEY uq_regions_name (region_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT='Sales regions used to group customers and employees.';

CREATE TABLE categories (
    category_id     INT          NOT NULL,
    category_name   VARCHAR(60)  NOT NULL,
    description     VARCHAR(200),
    warranty_months INT          NOT NULL DEFAULT 12
                    COMMENT 'Standard warranty in months for this category.',
    PRIMARY KEY (category_id),
    UNIQUE KEY uq_categories_name (category_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT='Product categories. warranty_months is the standard warranty for the category.';

CREATE TABLE suppliers (
    supplier_id   INT          NOT NULL,
    supplier_name VARCHAR(100) NOT NULL,
    contact_name  VARCHAR(80),
    city          VARCHAR(60),
    country       VARCHAR(60),
    phone         VARCHAR(30),
    email         VARCHAR(120),
    PRIMARY KEY (supplier_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT='Vendors that supply products.';

CREATE TABLE shippers (
    shipper_id   INT         NOT NULL,
    shipper_name VARCHAR(60) NOT NULL,
    phone        VARCHAR(30),
    PRIMARY KEY (shipper_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT='Logistics partners that deliver orders.';

CREATE TABLE employees (
    employee_id INT          NOT NULL,
    first_name  VARCHAR(50)  NOT NULL,
    last_name   VARCHAR(50)  NOT NULL,
    job_title   VARCHAR(60),
    email       VARCHAR(120),
    hire_date   DATE         NOT NULL,
    manager_id  INT          COMMENT 'Self reference to the reporting manager.',
    region_id   INT,
    PRIMARY KEY (employee_id),
    KEY idx_employees_manager (manager_id),
    KEY idx_employees_region  (region_id),
    CONSTRAINT fk_emp_manager FOREIGN KEY (manager_id) REFERENCES employees(employee_id),
    CONSTRAINT fk_emp_region  FOREIGN KEY (region_id)  REFERENCES regions(region_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT='Sales staff. manager_id is a self reference to the reporting manager.';

CREATE TABLE customers (
    customer_id    INT           NOT NULL,
    customer_name  VARCHAR(100)  NOT NULL,
    contact_name   VARCHAR(80),
    segment        VARCHAR(20)   NOT NULL
                   COMMENT 'Enterprise, Mid-Market, SMB, Government or Education.',
    city           VARCHAR(60),
    state_province VARCHAR(60),
    country        VARCHAR(60),
    region_id      INT,
    credit_limit   DECIMAL(12,2) DEFAULT 0
                   COMMENT 'Maximum outstanding balance allowed for the customer.',
    signup_date    DATE          NOT NULL,
    is_active      TINYINT(1)    NOT NULL DEFAULT 1,
    PRIMARY KEY (customer_id),
    KEY idx_customers_region (region_id),
    CONSTRAINT fk_cust_region FOREIGN KEY (region_id) REFERENCES regions(region_id),
    CONSTRAINT chk_cust_segment CHECK (segment IN
        ('Enterprise','Mid-Market','SMB','Government','Education'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT='Companies that place orders. segment drives the discount and payment terms.';

CREATE TABLE products (
    product_id     INT           NOT NULL,
    product_name   VARCHAR(120)  NOT NULL,
    category_id    INT           NOT NULL,
    supplier_id    INT           NOT NULL,
    unit_price     DECIMAL(10,2) NOT NULL COMMENT 'Current list price.',
    units_in_stock INT           NOT NULL DEFAULT 0,
    reorder_level  INT           NOT NULL DEFAULT 10,
    discontinued   TINYINT(1)    NOT NULL DEFAULT 0
                   COMMENT '1 means the product is no longer sold.',
    PRIMARY KEY (product_id),
    KEY idx_products_category (category_id),
    KEY idx_products_supplier (supplier_id),
    CONSTRAINT fk_prod_category FOREIGN KEY (category_id) REFERENCES categories(category_id),
    CONSTRAINT fk_prod_supplier FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT='Sellable items. unit_price is the current list price.';

-- ---------------------------------------------------------------------
-- Transaction tables
-- ---------------------------------------------------------------------
CREATE TABLE orders (
    order_id      INT           NOT NULL,
    customer_id   INT           NOT NULL,
    employee_id   INT           NOT NULL,
    shipper_id    INT,
    order_date    DATE          NOT NULL,
    required_date DATE,
    shipped_date  DATE          COMMENT 'NULL when not shipped yet or cancelled.',
    order_status  VARCHAR(20)   NOT NULL
                  COMMENT 'Completed, Shipped, Processing or Cancelled.',
    ship_city     VARCHAR(60),
    ship_country  VARCHAR(60),
    freight       DECIMAL(10,2) NOT NULL DEFAULT 0
                  COMMENT 'Delivery charge on the order header, not part of line revenue.',
    PRIMARY KEY (order_id),
    KEY idx_orders_customer (customer_id),
    KEY idx_orders_employee (employee_id),
    KEY idx_orders_shipper  (shipper_id),
    KEY idx_orders_date     (order_date),
    KEY idx_orders_status   (order_status),
    CONSTRAINT fk_ord_customer FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    CONSTRAINT fk_ord_employee FOREIGN KEY (employee_id) REFERENCES employees(employee_id),
    CONSTRAINT fk_ord_shipper  FOREIGN KEY (shipper_id)  REFERENCES shippers(shipper_id),
    CONSTRAINT chk_order_status CHECK (order_status IN
        ('Completed','Shipped','Processing','Cancelled'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT='Order header. One row per customer order. Cancelled orders have no payment.';

CREATE TABLE order_items (
    order_id     INT           NOT NULL,
    line_no      INT           NOT NULL,
    product_id   INT           NOT NULL,
    quantity     INT           NOT NULL,
    unit_price   DECIMAL(10,2) NOT NULL
                 COMMENT 'Price at the time of sale. May differ from products.unit_price.',
    discount_pct DECIMAL(5,2)  NOT NULL DEFAULT 0
                 COMMENT 'Line discount percentage, 0 to 20.',
    PRIMARY KEY (order_id, line_no),
    KEY idx_items_product (product_id),
    CONSTRAINT fk_item_order   FOREIGN KEY (order_id)   REFERENCES orders(order_id),
    CONSTRAINT fk_item_product FOREIGN KEY (product_id) REFERENCES products(product_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT='Order line detail. Revenue per line = quantity * unit_price * (1 - discount_pct/100).';

CREATE TABLE payments (
    payment_id     INT           NOT NULL,
    order_id       INT           NOT NULL,
    payment_date   DATE          NOT NULL,
    amount         DECIMAL(12,2) NOT NULL,
    payment_method VARCHAR(30)   NOT NULL,
    payment_status VARCHAR(20)   NOT NULL DEFAULT 'Cleared',
    PRIMARY KEY (payment_id),
    KEY idx_payments_order (order_id),
    CONSTRAINT fk_pay_order FOREIGN KEY (order_id) REFERENCES orders(order_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT='Customer payments received against an order.';

CREATE TABLE product_returns (
    return_id     INT           NOT NULL,
    order_id      INT           NOT NULL,
    product_id    INT           NOT NULL,
    return_date   DATE          NOT NULL,
    quantity      INT           NOT NULL,
    reason_code   VARCHAR(30)   NOT NULL
                  COMMENT 'DAMAGED, WRONG_ITEM, NOT_AS_DESCRIBED, LATE_DELIVERY or CHANGED_MIND.',
    refund_amount DECIMAL(12,2) NOT NULL,
    return_status VARCHAR(20)   NOT NULL DEFAULT 'Approved',
    PRIMARY KEY (return_id),
    KEY idx_returns_order   (order_id),
    KEY idx_returns_product (product_id),
    CONSTRAINT fk_ret_order   FOREIGN KEY (order_id)   REFERENCES orders(order_id),
    CONSTRAINT fk_ret_product FOREIGN KEY (product_id) REFERENCES products(product_id),
    CONSTRAINT chk_return_reason CHECK (reason_code IN
        ('DAMAGED','WRONG_ITEM','NOT_AS_DESCRIBED','LATE_DELIVERY','CHANGED_MIND'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT='Goods returned by customers with reason and refund value.';
