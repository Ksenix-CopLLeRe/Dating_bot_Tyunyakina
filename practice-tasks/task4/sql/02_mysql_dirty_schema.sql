DROP TABLE IF EXISTS accounts;

CREATE TABLE accounts (
    id INT PRIMARY KEY,
    owner_name VARCHAR(100) NOT NULL,
    balance INT NOT NULL,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE = InnoDB;

INSERT INTO accounts (id, owner_name, balance)
VALUES
    (1, 'Anna', 1000),
    (2, 'Sergey', 1000);
