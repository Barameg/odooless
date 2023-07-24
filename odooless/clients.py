import boto3
import env
import os

aws_access_key_id = os.environ.get("aws_access_key_id")
aws_secret_access_key = os.environ.get("aws_secret_access_key")
region_name = os.environ.get("region_name")

session = boto3.Session(
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key,
    region_name=region_name,
)

client = session.client('dynamodb')
resource = session.resource('dynamodb')
