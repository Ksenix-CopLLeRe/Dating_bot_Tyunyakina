DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS accounts;

CREATE TABLE accounts (
    id INTEGER PRIMARY KEY,
    owner_name TEXT NOT NULL,
    balance INTEGER NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    category TEXT NOT NULL,
    title TEXT NOT NULL,
    price INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO accounts (id, owner_name, balance)
VALUES
    (1, 'Alice', 1000),
    (2, 'Bob', 1000);

INSERT INTO products (category, title, price)
VALUES
    ('book', 'SQL basics', 700),
    ('book', 'PostgreSQL transactions', 1200),
    ('phone', 'Simple phone', 5000);
