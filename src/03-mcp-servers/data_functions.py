import json
from pydantic import BaseModel, Field

class Discount(BaseModel):
    discount_id: str
    discount_name: str
    discount_price: float
    product_id: str
    discount_volume: int

class Product(BaseModel):
    product_id: str
    product_name: str
    list_price: float
    description: str
    features: list[str]

class CustomerDiscount(BaseModel):
    customer_id: str
    discount_id: str
    discount_name: str
    discount_price: float
    product_id: str
    discount_volume: int

class Supplier(BaseModel):
    supplier_id: str
    supplier_name: str
    contract_id: str
    contract_name: str
    products: list[Product] = Field(None)
    discounts: list[Discount] = Field(None)

class Customer(BaseModel):
    customer_id: str
    customer_name: str
    customer_address: str
    customer_phone: str
    customer_email: str
    customer_discount: list[CustomerDiscount] = Field(None)

class ProductInventory(BaseModel):
    product_id: str
    product_name: str
    volume: int
    location: str

class Order(BaseModel):
    customer_id: str
    order_id: str
    order_date: str
    order_status: str
    fill_date: str
    fill_strategy: str = None
    order_items: list[Product] = None

class Message(BaseModel):
    message: str

class DataLayer(BaseModel):
    suppliers: list[Supplier] = Field(None)
    customers: list[Customer] = Field(None)
    orders: list[Order] = Field(None)
    inventory: list[ProductInventory] = Field(None)

    def fill_data(self):
        self.suppliers = self.generate_supplier_data()
        self.customers = self.generate_customer_data()
        self.orders = self.generate_order_data()
        self.inventory = self.generate_inventory_data()

    def load_supplier_from_json(self, file_name: str):
        """
        Loads supplier data from a JSON file.
        :param file_name (str): The name of the file to load the data from.
        """
        try:
            with open(file_name, 'r') as f:
                data = json.load(f)
                self.suppliers = [Supplier(**supplier) for supplier in data["suppliers"]]
            print("Loaded suppliers:", len(self.suppliers))
        except IOError as e:
            raise ValueError(f"Error loading file: {e}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Error decoding JSON: {e}")
        
    def save_supplier_to_json(self, file_name: str):
        """
        Saves supplier data to a JSON file.
        :param file_name (str): The name of the file to save the data to.
        """
        try:
            print(self.suppliers)
            with open(file_name, 'w') as f:
                json.dump({"suppliers": [supplier.dict() for supplier in self.suppliers]}, f, indent=4)
        except IOError as e:
            raise ValueError(f"Error saving to file: {e}")
    
    def generate_customer_data(self) -> list[Customer]:
        """
        Generates a list of 10 customers with mock data.
        Each customer has a list of 3 discounts according to product volume.
        :return: List of customers.
        :rtype: list[Customer]
        """
        return [
            Customer(
                customer_id=f"CUST{i}",
                customer_name=f"Customer {i}",
                customer_address=f"Address {i}",
                customer_phone=f"Phone {i}",
                customer_email=f"   Email {i}",
                customer_discount=[
                    CustomerDiscount(
                        customer_id=f"CUST{i}",
                        discount_id=f"DISCOUNT{j}",
                        discount_name=f"Discount {j}",
                        discount_price=5.0 + j,
                        product_id=f"PROD{j}",
                        discount_volume=j * 10
                    ) for j in range(3)
                ]
            ) for i in range(10)
        ]

    def save_customer_to_json(self, file_name: str):
        """
        Saves customer data to a JSON file.
        :param file_name (str): The name of the file to save the data to.
        """
        try:
            with open(file_name, 'w') as f:
                json.dump({"customers": [customer.dict() for customer in self.customers]}, f, indent=4)
        except IOError as e:
            raise ValueError(f"Error saving to file: {e}")
        
    def load_customer_from_json(self, file_name: str):  
        """
        Loads customer data from a JSON file.
        :param file_name (str): The name of the file to load the data from.
        """
        try:
            with open(file_name, 'r') as f:
                data = json.load(f)
                self.customers = [Customer(**customer) for customer in data["customers"]]
            print("Loaded customers:", len(self.customers))
        except IOError as e:
            raise ValueError(f"Error loading file: {e}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Error decoding JSON: {e}")

    def generate_order_data(self) -> list[Order]:
        """
        Generates a list of 10 orders with mock data.
        Each order has a list of 3 products.
        :return: List of orders.
        :rtype: list[Order]
        """
        return [
            Order(
                customer_id=f"CUST{i}",
                order_id=f"ORDER{i}",
                order_date="2023-10-01",
                order_status="Pending",
                fill_date="2023-10-02",
                fill_strategy="Standard",
                order_items=[
                    Product(
                        product_id=f"PROD{j}",
                        product_name=f"Product {j}",
                        list_price=10.0 + j,
                        description=f"Description for Product {j}",
                        features=["Feature 1", "Feature 2"]
                    ) for j in range(3)
                ]
            ) for i in range(10)
        ]

    def load_order_from_json(self, file_name: str):
        """
        Loads order data from a JSON file.
        :param file_name (str): The name of the file to load the data from.
        """
        try:
            with open(file_name, 'r') as f:
                data = json.load(f)
                self.orders = [Order(**order) for order in data["orders"]]
            print("Loaded orders:", len(self.orders))
        except IOError as e:
            raise ValueError(f"Error loading file: {e}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Error decoding JSON: {e}")
    
    def save_order_to_json(self, file_name: str):   
        """
        Saves order data to a JSON file.
        :param file_name (str): The name of the file to save the data to.
        """
        try:
            with open(file_name, 'w') as f:
                json.dump({"orders": [order.dict() for order in self.orders]}, f, indent=4)
        except IOError as e:
            raise ValueError(f"Error saving to file: {e}")

    def generate_supplier_data(self) -> list[Supplier]:
        """
        Generates a list of 10 suppliers with mock data for retail products and household items across the spectrum from Unilever to local suppliers.
        Each supplier has a list of 3 products and 3 discounts according to product volume. Products are Shampoo, Soap, and Toothpaste.
        :return: List of suppliers.
        :rtype: list[Supplier]
        """
        return [
            Supplier(
                supplier_id=f"SUPP{i}",
                supplier_name=f"Supplier {i}",
                contract_id=f"CONTRACT{i}",
                contract_name=f"Contract {i}",
                products=[
                    Product(
                        product_id=f"PROD{j}",
                        product_name=f"Product {j}",
                        list_price=10.0 + j,
                        description=f"Description for Product {j}",
                        features=["Feature 1", "Feature 2"]
                    ) for j in range(3)
                ],
                discounts=[
                    Discount(
                        discount_id=f"DISCOUNT{j}",
                        discount_name=f"Discount {j}",
                        discount_price=5.0 + j,
                        product_id=f"PROD{j}",
                        discount_volume=j * 10
                    ) for j in range(3)
                ]
            ) for i in range(10)
        ]
    
    def generate_inventory_data(self) -> list[ProductInventory]:
        """
        Generates a list of 10 products with mock data for inventory.
        Each product has a volume and location.
        :return: List of products in the inventory.
        :rtype: list[ProductInventory]
        """
        return [
            ProductInventory(
                product_id=f"PROD{i}",
                product_name=f"Product {i}",
                volume=i * 10,
                location=f"Location {i}"
            ) for i in range(10)
        ]

    def get_supplier_by_id(self, supplier_id: str) -> Supplier:
        """
        Fetches a supplier by its ID.

        :param supplier_id (str): The ID of the supplier to fetch.
        :return: The supplier object.
        :rtype: Supplier
        """
        for supplier in self.suppliers:
            if supplier.supplier_id == supplier_id:
                return supplier
        return None
    
    def get_customer_by_id(self, customer_id: str) -> Customer:
        """
        Fetches a customer by its ID.

        :param customer_id (str): The ID of the customer to fetch.
        :return: The customer object.
        :rtype: Customer
        """
        for customer in self.customers:
            if customer.customer_id == customer_id:
                return customer
        return None
    
    def get_customer_by_name(self, customer_name: str) -> Customer:
        """
        Fetches a customer by its ID.

        :param customer_id (str): The ID of the customer to fetch.
        :return: The customer object.
        :rtype: Customer
        """
        for customer in self.customers:
            if customer.customer_name == customer_name:
                return customer
        return None
    
    def get_order_by_id(self, order_id: str) -> Order:
        """
        Fetches an order by its ID.

        :param order_id (str): The ID of the order to fetch.
        :return: The order object.
        :rtype: Order
        """
        for order in self.orders:
            if order.order_id == order_id:
                return order
        return None
    
    def get_orders_by_customer_id(self, customer_id: str) -> list[Order]:
        """
        Fetches all orders for a given customer ID.

        :param customer_id (str): The ID of the customer to fetch orders for.
        :return: List of order objects.
        :rtype: list[Order]
        """
        return [order for order in self.orders if order.customer_id == customer_id]

    def get_all_products(self) -> list[Product]:
        """
        Fetches all products from all suppliers.

        :return: List of product objects.
        :rtype: list[Product]
        """
        products = []
        for supplier in self.suppliers:
            products.extend(supplier.products)
        return products

    def get_all_discounts(self) -> list[Discount]:
        """
        Fetches all discounts from all suppliers.

        :return: List of discount objects.
        :rtype: list[Discount]
        """
        discounts = []
        for supplier in self.suppliers:
            discounts.extend(supplier.discounts)
        return discounts
    
    def update_order(self, order_id: str, order_data: Order) -> bool:
        """
        Updates an existing order with new data.

        :param order_id (str): The ID of the order to update.
        :param order_data (Order): The new order data.
        :return: True if the order was updated successfully, False otherwise.
        :rtype: bool
        """
        for i, order in enumerate(self.orders):
            if order.order_id == order_id:
                self.orders[i] = order_data
                return True
        return False

    def load_inventory_from_json(self, file_name: str):
        """
        Loads inventory data from a JSON file.
        :param file_name (str): The name of the file to load the data from.
        """
        try:
            with open(file_name, 'r') as f:
                data = json.load(f)
                self.inventory = [ProductInventory(**product) for product in data["inventory"]]
            print("Loaded inventory:", len(self.inventory))            
        except IOError as e:
            raise ValueError(f"Error loading file: {e}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Error decoding JSON: {e}")
        
    def get_inventory_by_product_id(self, product_id: str) -> list[ProductInventory]:
        """
        Fetches all inventory items for a given product ID.
        This function returns a list of inventory items that match the given product ID.
        It is useful for checking the availability of a specific product in the inventory.  

        :param
        product_id (str): The ID of the product to fetch inventory for.
        :return: The inventory object.
        :rtype: ProductInventory
        """
        inventory = []
        for item in self.inventory:
            if item.product_id == product_id:
                inventory.append(item)
        return inventory

