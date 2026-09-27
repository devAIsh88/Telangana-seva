import json
import boto3
from boto3.dynamodb.types import TypeDeserializer

s3 = boto3.client('s3')
deserializer = TypeDeserializer()

# Matches your established AWS configuration
S3_BUCKET = "telangana-seva-bot-data" 

def lambda_handler(event, context):
    records_processed = 0
    
    for record in event.get('Records', []):
        # We only care about items that DynamoDB is DELETING (via TTL expiration)
        if record['eventName'] == 'REMOVE':
            try:
                # DynamoDB sends data in a weird nested format. This converts it back to normal JSON.
                raw_data = record['dynamodb']['OldImage']
                clean_data = {k: deserializer.deserialize(v) for k, v in raw_data.items()}
                
                session_id = clean_data.get('session_id', 'unknown_session')
                query_id = clean_data.get('query_id', 'unknown_query')
                
                # Establish logical directory mapping inside S3 cold storage
                s3_key = f"chat_archives/{session_id}/{query_id}.json"
                
                # Push the expired chat to S3 permanently
                s3.put_object(
                    Bucket=S3_BUCKET,
                    Key=s3_key,
                    Body=json.dumps(clean_data, default=str),
                    ContentType='application/json'
                )
                records_processed += 1
                print(f"[ARCHIVE SUCCESS] Migrated query {query_id} to S3 Cold Storage.")
                
            except Exception as e:
                print(f"[ARCHIVE ERROR] Processing exception: {str(e)}")
                
    return {
        'statusCode': 200,
        'body': f"Successfully migrated {records_processed} expired interaction records to S3 Cold Storage."
    }