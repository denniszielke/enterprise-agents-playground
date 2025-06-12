import uvicorn
import os
from dotenv import load_dotenv
import asyncio
from fastmcp import FastMCP
from fastmcp.server.dependencies import get_http_request
from starlette.requests import Request

from data_functions import DataLayer
from data_functions import Discount, Product, Order, Supplier, Customer, ProductInventory

script_dir = os.path.dirname(os.path.abspath(__file__))
data_path = os.path.join(script_dir, "data")
data_layer = DataLayer()
data_layer.load_order_from_json(os.path.join(data_path, "orders.json"))
data_layer.load_supplier_from_json(os.path.join(data_path, "suppliers.json"))
data_layer.load_customer_from_json(os.path.join(data_path, "customers.json"))
data_layer.load_inventory_from_json(os.path.join(data_path, "inventory.json"))
load_dotenv()

mcp = FastMCP("EcommerceAPIs", "1.0.0")

sse_app = mcp.http_app(path="/sse", transport="sse")

@mcp.resource("config://version")
def get_version() -> dict: 
    return {
        "version": "1.2.0",
        "features": ["tools", "resources"],
    }

@mcp.resource("resource://customers/{customer_id}/customer")
async def get_customer_by_id(customer_id: str) -> Customer:
    """Gets details of a customer by customer id"""
    return data_layer.get_customer_by_id(customer_id)

@mcp.resource("resource://customers/{customer_name}/customer")
async def get_customer_by_name(customer_name: str) -> Customer:
    """Gets details of a customer by name"""
    return data_layer.get_customer_by_name(customer_name)

@mcp.resource("resource://products/products")
async def get_all_products() -> list[Product]:
    """Gets all products"""
    return data_layer.get_all_products()

@mcp.resource("resource://discounts/discount")
async def get_all_discounts() -> list[Discount]:
    """Gets all discounts"""
    return data_layer.get_all_discounts()

@mcp.resource("resource://orders/{order_id}/order")
async def get_order_by_id(order_id: str) -> Order:
    """Gets details of an order by ID"""
    return data_layer.get_order_by_id(order_id)

@mcp.tool()
async def update_order(order_id: str, order: Order) -> bool:
    """Updates an existing order by referencing the order ID"""
    print("received order update")
    return data_layer.update_order(order_id, order)

@mcp.resource("resource://inventory/{product_id}/productinventory")
async def get_inventory_by_product_id(product_id: str) -> list[ProductInventory]:
    """Gets inventory details by product ID"""
    return data_layer.get_inventory_by_product_id(product_id)

@mcp.resource("resource://inventory/{customer_name}/location")
async def get_closest_inventory_location(customer_name: str) -> str:
    """Gets the closest inventory location based on customer name"""
    customer_details = data_layer.get_customer_by_name(customer_name)
    if customer_details is None:
        return "Customer location unknown"
    
    if "Germany" in customer_details.address:
        return "EuropeWest"
    elif "IL" in customer_details.address:
        return "USEast"
    else:
        return "EuropeWest"

async def check_mcp(mcp: FastMCP):
    # List the components that were created
    tools = await mcp.get_tools()
    resources = await mcp.get_resources()
    templates = await mcp.get_resource_templates()
    
    print(
        f"{len(tools)} Tool(s): {', '.join([t.name for t in tools.values()])}"
    )
    print(
        f"{len(resources)} Resource(s): {', '.join([r.name for r in resources.values()])}"
    )
    print(
        f"{len(templates)} Resource Template(s): {', '.join([t.name for t in templates.values()])}"
    )
    
    return mcp

if __name__ == "__main__":
    try:
        asyncio.run(check_mcp(mcp))
        uvicorn.run(sse_app, host="0.0.0.0", port=8000)
    except KeyboardInterrupt:
        print("\nProgram interrupted by user. Cleaning up...")
    except Exception as e:
        print(f"An error occurred: {e}")