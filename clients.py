import boto3
import env


aws_access_key_id = env.aws_access_key_id
aws_secret_access_key = env.aws_secret_access_key
region_name = env.region_name

session = boto3.Session(
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key,
    region_name=region_name,
)

client = session.client('dynamodb')
resource = session.resource('dynamodb')
