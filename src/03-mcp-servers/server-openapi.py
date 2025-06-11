import logging
import sys
import os
import asyncio
from dotenv import load_dotenv

import uvicorn
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from data_functions import DataLayer
from data_functions import Discount, Product, Order, Supplier, Customer, ProductInventory, Message

data_layer = DataLayer()
data_layer.load_order_from_json("data/orders.json")
data_layer.load_supplier_from_json("data/suppliers.json")
data_layer.load_customer_from_json("data/customers.json")
data_layer.load_inventory_from_json("data/inventory.json")

load_dotenv()

app = FastAPI()

origins = [
    os.getenv("TUNNEL_DNS"),
    "http://localhost",
    "http://localhost:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="EcommerceAPI",
        version="1.0.0",
        routes=app.routes,
        openapi_version="3.0.1"
    )
    openapi_schema["servers"] = [
        {
        "url": "https://" + os.getenv("CONTAINER_APP_NAME") + "." + os.getenv("CONTAINER_APP_ENV_DNS_SUFFIX") if os.getenv("CONTAINER_APP_ENV_DNS_SUFFIX") is not None else "http://localhost:8000"
        }
    ]

    app.openapi_schema = openapi_schema
    return app.openapi_schema

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("webhost")

logging.basicConfig(
    stream=sys.stdout, level=logging.INFO
) 

@app.get("/customers/id/{customer_id}", operation_id="get_customer_by_id", responses={404: {"model": Message}})
async def get_customer_by_id(customer_id: str) -> Customer:
    """Get customer by ID"""
    item = data_layer.get_customer_by_id(customer_id)
    if item is None:
        logger.error(f"Customer with ID {customer_id} not found")
        return JSONResponse(
            status_code=404,
            content={"message": f"Customer with ID {customer_id} not found"},
        )
    logger.info(f"Customer with ID {customer_id} found")
    return item

@app.get("/customers/name/{customer_name}", operation_id="get_customer_by_name", responses={404: {"model": Message}})
async def get_customer_by_name(customer_name: str) -> Customer:
    """Get customer by name"""
    item = data_layer.get_customer_by_name(customer_name)
    if item is None:
        logger.error(f"Customer with name {customer_name} not found")
        return JSONResponse(
            status_code=404,
            content={"message": f"Customer with name {customer_name} not found"},
        )
    logger.info(f"Customer with name {customer_name} found")
    return item

@app.get("/products/all", operation_id="get_all_products", responses={404: {"model": Message}})
async def get_all_products() -> list[Product]:
    """Get all products"""
    items = data_layer.get_all_products()
    if not items:
        logger.error("No products found")
        return JSONResponse(
            status_code=404,
            content={"message": "No products found"},
        )
    logger.info(f"{len(items)} products found")
    return items

@app.get("/discounts/all", operation_id="get_all_discounts", responses={404: {"model": Message}})
async def get_all_discounts() -> list[Discount]:
    """Get all discounts"""
    items = data_layer.get_all_discounts()
    if not items:
        logger.error("No discounts found")
        return JSONResponse(
            status_code=404,
            content={"message": "No discounts found"},
        )
    logger.info(f"{len(items)} discounts found")
    return items

@app.get("/orders/id/{order_id}", operation_id="get_order_by_id", responses={404: {"model": Message}})
async def get_order_by_id(order_id: str) -> Order:
    """Get order by ID"""
    item = data_layer.get_order_by_id(order_id)
    if item is None:
        logger.error(f"Order with ID {order_id} not found")
        return JSONResponse(
            status_code=404,
            content={"message": f"Order with ID {order_id} not found"},
        )
    logger.info(f"Order with ID {order_id} found")
    return item

@app.post("/order/update", operation_id="update_order", responses={404: {"model": Message}})
async def update_order(order: Order) -> bool:
    """Update existing order"""
    logger.info(f"Received order update for order ID: {order.order_id}")
    updated = data_layer.update_order(order.order_id, order)
    if not updated:
        logger.error(f"Order with ID {order.order_id} not found for update")
        return JSONResponse(
            status_code=404,
            content={"message": f"Order with ID {order.order_id} not found for update"},
        )
    logger.info(f"Order with ID {order.order_id} updated")
    return updated

@app.get("/get_closest_inventory_location/{customer_name}", operation_id="get_closest_inventory_location", responses={404: {"model": Message}})
async def get_closest_inventory_location(customer_name: str) -> str:
    """Get closest inventory location based on customer name"""
    customer_details = data_layer.get_customer_by_name(customer_name)
    if customer_details is None:
        logger.error(f"Customer with name {customer_name} not found")
        return "EuropeWest"
    if "Germany" in customer_details.address:
        return "EuropeWest"
    elif "IL" in customer_details.address:
        return "USEast"
    else:
        return "EuropeWest"

@app.get("/inventory/{product_id}", operation_id="get_inventory_by_product_id", responses={404: {"model": Message}})
async def get_inventory_by_product_id(product_id: str) -> list[ProductInventory]:
    """Get available inventory by product ID"""
    items = data_layer.get_inventory_by_product_id(product_id)
    if not items:
        logger.error(f"No inventory found for product ID {product_id}")
        return JSONResponse(
            status_code=404,
            content={"message": f"No inventory found for product ID {product_id}"},
        )
    logger.info(f"Inventory found for product ID {product_id}")
    return items

app.openapi = custom_openapi

if __name__ == "__main__":
    try:
        uvicorn.run(app, host="0.0.0.0", port=8000)
    except Exception as e:
        print(e)
        sys.exit(0)