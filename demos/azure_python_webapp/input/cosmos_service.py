"""Azure Cosmos DB operations — CRUD, queries, and stored procedures."""

from azure.cosmos import CosmosClient, PartitionKey, exceptions
from config import AZURE_COSMOS_ENDPOINT, AZURE_COSMOS_KEY, AZURE_COSMOS_DATABASE, AZURE_COSMOS_CONTAINER


def get_cosmos_client():
    """Create an Azure CosmosClient from endpoint and key."""
    return CosmosClient(AZURE_COSMOS_ENDPOINT, credential=AZURE_COSMOS_KEY)


def get_container():
    """Get the Cosmos DB container client, creating database and container if needed."""
    client = get_cosmos_client()
    database = client.create_database_if_not_exists(id=AZURE_COSMOS_DATABASE)
    container = database.create_container_if_not_exists(
        id=AZURE_COSMOS_CONTAINER,
        partition_key=PartitionKey(path="/category"),
    )
    return container


def create_item(item):
    """Insert a new item into the Cosmos DB container."""
    container = get_container()
    return container.create_item(body=item)


def read_item(item_id, partition_key):
    """Read a single item from Cosmos DB by ID and partition key."""
    container = get_container()
    return container.read_item(item=item_id, partition_key=partition_key)


def update_item(item_id, partition_key, updates):
    """Update an existing item in Cosmos DB via upsert."""
    container = get_container()
    existing = container.read_item(item=item_id, partition_key=partition_key)
    existing.update(updates)
    return container.upsert_item(body=existing)


def delete_item(item_id, partition_key):
    """Delete an item from Cosmos DB."""
    container = get_container()
    container.delete_item(item=item_id, partition_key=partition_key)


def query_items(query_text, parameters=None):
    """Run a SQL query against the Cosmos DB container."""
    container = get_container()
    results = container.query_items(
        query=query_text,
        parameters=parameters or [],
        enable_cross_partition_query=True,
    )
    return list(results)


def execute_stored_procedure(sproc_id, partition_key, params):
    """Execute a stored procedure in Cosmos DB."""
    container = get_container()
    return container.scripts.execute_stored_procedure(
        sproc=sproc_id,
        params=params,
        partition_key=partition_key,
    )
