import logging
import sys
import os
from dotenv import load_dotenv
from typing import Any

from typing import List
from mcp.server.fastmcp import FastMCP

from data_functions import DataLayer
from data_functions import Discount, Product, Order, Supplier, Customer

script_dir = os.path.dirname(os.path.abspath(__file__))
data_path = os.path.join(script_dir, "data")
data_layer = DataLayer()
data_layer.load_order_from_json(os.path.join(data_path, "orders.json"))
data_layer.load_supplier_from_json(os.path.join(data_path, "suppliers.json"))
data_layer.load_customer_from_json(os.path.join(data_path, "customers.json"))

load_dotenv()

mcp = FastMCP("E-commerce")

@mcp.tool()
async def get_customer_by_id(customer_id: str) -> Customer:
    """Gets details of a customer by ID"""
    return data_layer.get_customer_by_id(customer_id)

@mcp.tool()
async def get_customer_by_name(customer_name: str) -> Customer:
    """Gets details of a customer by name"""
    return data_layer.get_customer_by_name(customer_name)

@mcp.tool()
async def get_all_products() -> list[Product]:
    """Gets all products"""
    return data_layer.get_all_products()

@mcp.tool()
async def get_all_discounts() -> list[Discount]:
    """Gets all discounts"""
    return data_layer.get_all_discounts()

@mcp.tool()
async def get_order_by_id(order_id: str) -> Order:
    """Gets details of an order by ID"""
    return data_layer.get_order_by_id(order_id)

@mcp.tool()
async def update_order(order_id: str, order: Order) -> bool:
    """Updates an existing order by referencing the order ID"""
    print("received order update")
    return data_layer.update_order(order_id, order)

if __name__ == "__main__":
    mcp.run(transport="stdio")