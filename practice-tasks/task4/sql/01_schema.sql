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
    (1, 'Anna', 1000),
    (2, 'Sergey', 1000);

INSERT INTO products (category, title, price)
VALUES
    ('book', 'Harry Potter', 700),
    ('book', 'All for the game', 1200),
    ('phone', 'Samsung Ultra Flip Flop Z', 5000);
