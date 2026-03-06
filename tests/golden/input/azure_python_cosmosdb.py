from azure.cosmos import CosmosClient, PartitionKey

endpoint = "https://mycosmosaccount.documents.azure.com:443/"
key = "my-key"
client = CosmosClient(endpoint, key)
database = client.get_database_client("mydb")
container = database.get_container_client("items")


def create_item(item):
    """Create an item in Cosmos DB."""
    container.create_item(body=item)


def read_item(item_id, partition_key):
    """Read an item from Cosmos DB."""
    return container.read_item(item=item_id, partition_key=partition_key)


def query_items(query, parameters=None):
    """Query items from Cosmos DB."""
    return list(container.query_items(
        query=query,
        parameters=parameters,
        enable_cross_partition_query=True
    ))


def delete_item(item_id, partition_key):
    """Delete an item from Cosmos DB."""
    container.delete_item(item=item_id, partition_key=partition_key)
