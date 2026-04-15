import sqlite3
from datetime import datetime

def get_db_connection():
    return sqlite3.connect('store.db')

def scenario1_place_order(customer_id, items):
    conn = get_db_connection()
    try:
        conn.execute('BEGIN')
        
        order_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor = conn.execute(
            'INSERT INTO Orders (CustomerID, OrderDate, TotalAmount) VALUES (?, ?, 0)',
            (customer_id, order_date)
        )
        order_id = cursor.lastrowid
        
        total = 0
        for product_id, quantity in items:
            cursor = conn.execute('SELECT Price FROM Products WHERE ProductID = ?', (product_id,))
            price = cursor.fetchone()[0]
            subtotal = price * quantity
            total += subtotal
            
            conn.execute(
                'INSERT INTO OrderItems (OrderID, ProductID, Quantity, Subtotal) VALUES (?, ?, ?, ?)',
                (order_id, product_id, quantity, subtotal)
            )
        
        conn.execute('UPDATE Orders SET TotalAmount = ? WHERE OrderID = ?', (total, order_id))
        conn.commit()
        print(f"Order #{order_id} created for {total} rub")
        return order_id
        
    except Exception as e:
        conn.rollback()
        print(f"Error: {e}")
        return None
    finally:
        conn.close()

def scenario2_update_email(customer_id, new_email):
    conn = get_db_connection()
    try:
        conn.execute('BEGIN')
        
        cursor = conn.execute('SELECT CustomerID FROM Customers WHERE CustomerID = ?', (customer_id,))
        if not cursor.fetchone():
            raise Exception(f"Customer with ID {customer_id} not found")
        
        conn.execute(
            'UPDATE Customers SET Email = ? WHERE CustomerID = ?',
            (new_email, customer_id)
        )
        
        conn.commit()
        print(f"Email for customer #{customer_id} updated to {new_email}")
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"Error: {e}")
        return False
    finally:
        conn.close()

def scenario3_add_product(name, price):
    conn = get_db_connection()
    try:
        conn.execute('BEGIN')
        
        if price <= 0:
            raise Exception("Price must be greater than 0")
        
        cursor = conn.execute(
            'INSERT INTO Products (ProductName, Price) VALUES (?, ?)',
            (name, price)
        )
        
        conn.commit()
        product_id = cursor.lastrowid
        print(f"Product '{name}' added with ID #{product_id}, price {price} rub")
        return product_id
        
    except Exception as e:
        conn.rollback()
        print(f"Error: {e}")
        return None
    finally:
        conn.close()

def show_data():
    conn = get_db_connection()
    print("\n" + "="*50)
    
    print("\nCustomers:")
    for row in conn.execute('SELECT * FROM Customers'):
        print(f"  {row}")
    
    print("\nProducts:")
    for row in conn.execute('SELECT * FROM Products'):
        print(f"  {row}")
    
    print("\nOrders:")
    for row in conn.execute('SELECT * FROM Orders'):
        print(f"  {row}")
    
    print("\nOrderItems:")
    for row in conn.execute('SELECT * FROM OrderItems'):
        print(f"  {row}")
    
    conn.close()

def main():
    print("Online Store Transactions Demo\n")
    
    show_data()
    
    print("\n" + "="*50)
    print("Scenario 3: Add new product")
    scenario3_add_product("Monitor", 25000.00)
    
    print("\n" + "="*50)
    print("Scenario 1: Place order")
    scenario1_place_order(1, [(1, 2), (2, 3)])
    
    print("\n" + "="*50)
    print("Scenario 2: Update customer email")
    scenario2_update_email(1, "ivan.new@example.com")
    
    show_data()

if __name__ == "__main__":
    main()