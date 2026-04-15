import sqlite3
from datetime import datetime

DB_PATH = '/app/data/store.db'

def get_db_connection():
    return sqlite3.connect(DB_PATH)

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
        print(f"Заказ #{order_id} создан на сумму {total} руб.")
        return order_id
        
    except Exception as e:
        conn.rollback()
        print(f"Ошибка: {e}")
        return None
    finally:
        conn.close()

def scenario2_update_email(customer_id, new_email):
    conn = get_db_connection()
    try:
        conn.execute('BEGIN')
        
        cursor = conn.execute('SELECT CustomerID FROM Customers WHERE CustomerID = ?', (customer_id,))
        if not cursor.fetchone():
            raise Exception(f"Клиент с ID {customer_id} не найден")
        
        conn.execute(
            'UPDATE Customers SET Email = ? WHERE CustomerID = ?',
            (new_email, customer_id)
        )
        
        conn.commit()
        print(f"Email для клиента #{customer_id} обновлен на {new_email}")
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"Ошибка: {e}")
        return False
    finally:
        conn.close()

def scenario3_add_product(name, price):
    conn = get_db_connection()
    try:
        conn.execute('BEGIN')
        
        if price <= 0:
            raise Exception("Цена должна быть больше 0")
        
        cursor = conn.execute(
            'INSERT INTO Products (ProductName, Price) VALUES (?, ?)',
            (name, price)
        )
        
        conn.commit()
        product_id = cursor.lastrowid
        print(f"Товар '{name}' добавлен с ID #{product_id}, цена {price} руб.")
        return product_id
        
    except Exception as e:
        conn.rollback()
        print(f"Ошибка: {e}")
        return None
    finally:
        conn.close()

def show_data():
    conn = get_db_connection()
    print("\n" + "="*50)
    
    print("\nКлиенты:")
    for row in conn.execute('SELECT * FROM Customers'):
        print(f"  {row}")
    
    print("\nТовары:")
    for row in conn.execute('SELECT * FROM Products'):
        print(f"  {row}")
    
    print("\nЗаказы:")
    for row in conn.execute('SELECT * FROM Orders'):
        print(f"  {row}")
    
    print("\nПозиции заказов:")
    for row in conn.execute('SELECT * FROM OrderItems'):
        print(f"  {row}")
    
    conn.close()

def main():    
    show_data()
    
    print("\n" + "="*50)
    print("Сценарий 3: Добавление нового товара")
    scenario3_add_product("Пасха", 350.00)
    
    print("\n" + "="*50)
    print("Сценарий 1: Размещение заказа")
    scenario1_place_order(1, [(1, 3), (2, 2)])
    
    print("\n" + "="*50)
    print("Сценарий 2: Обновление email клиента")
    scenario2_update_email(1, "gulcim.new@gmail.com")
    
    show_data()

if __name__ == "__main__":
    main()