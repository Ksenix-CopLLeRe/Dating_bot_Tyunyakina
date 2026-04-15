import sqlite3
import os

def init_database():
    db_path = '/app/data/store.db'
    
    conn = sqlite3.connect(db_path)
    
    conn.execute('''
    CREATE TABLE IF NOT EXISTS Customers (
        CustomerID INTEGER PRIMARY KEY AUTOINCREMENT,
        FirstName TEXT NOT NULL,
        LastName TEXT NOT NULL,
        Email TEXT UNIQUE NOT NULL
    )
    ''')
    
    conn.execute('''
    CREATE TABLE IF NOT EXISTS Products (
        ProductID INTEGER PRIMARY KEY AUTOINCREMENT,
        ProductName TEXT NOT NULL,
        Price REAL NOT NULL CHECK (Price > 0)
    )
    ''')
    
    conn.execute('''
    CREATE TABLE IF NOT EXISTS Orders (
        OrderID INTEGER PRIMARY KEY AUTOINCREMENT,
        CustomerID INTEGER,
        OrderDate TEXT NOT NULL,
        TotalAmount REAL DEFAULT 0,
        FOREIGN KEY (CustomerID) REFERENCES Customers(CustomerID)
    )
    ''')
    
    conn.execute('''
    CREATE TABLE IF NOT EXISTS OrderItems (
        OrderItemID INTEGER PRIMARY KEY AUTOINCREMENT,
        OrderID INTEGER,
        ProductID INTEGER,
        Quantity INTEGER NOT NULL CHECK (Quantity > 0),
        Subtotal REAL NOT NULL,
        FOREIGN KEY (OrderID) REFERENCES Orders(OrderID),
        FOREIGN KEY (ProductID) REFERENCES Products(ProductID)
    )
    ''')
    
    conn.execute('''
    INSERT OR IGNORE INTO Customers (FirstName, LastName, Email) 
    VALUES ('Гульсим', 'Гульсимова', 'glsm@gmail.com')
    ''')
    
    conn.execute('''
    INSERT OR IGNORE INTO Customers (FirstName, LastName, Email) 
    VALUES ('Евгений', 'Евгениев', 'evgenij@gmail.com')
    ''')
    
    conn.execute('''
    INSERT OR IGNORE INTO Customers (FirstName, LastName, Email) 
    VALUES ('Сергей', 'Сергеев', 'sergserg@gmail.com')
    ''')
    
    conn.execute('''
    INSERT OR IGNORE INTO Products (ProductName, Price) 
    VALUES ('Хлеб', 50.00)
    ''')
    
    conn.execute('''
    INSERT OR IGNORE INTO Products (ProductName, Price) 
    VALUES ('Молоко', 89.99)
    ''')
    
    conn.execute('''
    INSERT OR IGNORE INTO Products (ProductName, Price) 
    VALUES ('Кулич', 215.49)
    ''')
    
    conn.commit()
    conn.close()
    
    print("База данных успешно инициализирована")

if __name__ == "__main__":
    init_database()