import boto3

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('users')


def put_user(user_id, name, email):
    """Add a user to DynamoDB."""
    table.put_item(Item={
        'id': user_id,
        'name': name,
        'email': email,
    })


def get_user(user_id):
    """Get a user from DynamoDB."""
    response = table.get_item(Key={'id': user_id})
    return response.get('Item')


def query_users_by_email(email):
    """Query users by email."""
    response = table.query(
        IndexName='email-index',
        KeyConditionExpression='email = :email',
        ExpressionAttributeValues={':email': email}
    )
    return response['Items']


def delete_user(user_id):
    """Delete a user from DynamoDB."""
    table.delete_item(Key={'id': user_id})
