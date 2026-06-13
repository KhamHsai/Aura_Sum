# Database Plan

This document outlines the planned database structure in MySQL.

## Tables

### 1. Categories (`categories`)
- `id` (int, PK, autoincrement)
- `name` (varchar, unique, index)
- `description` (text, optional)

### 2. Expenses (`expenses`)
- `id` (int, PK, autoincrement)
- `store_name` (varchar)
- `transaction_date` (datetime)
- `total_amount` (decimal)
- `category_id` (int, FK references categories)
- `receipt_url` (varchar, optional)
- `raw_gemini_output` (text, optional)
- `created_at` (datetime)

### 3. Expense Items (`expense_items`)
- `id` (int, PK, autoincrement)
- `expense_id` (int, FK references expenses)
- `item_name` (varchar)
- `quantity` (int)
- `unit_price` (decimal)
- `total_price` (decimal)
