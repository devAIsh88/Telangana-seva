import boto3
from datetime import datetime

dynamodb = boto3.resource(
    "dynamodb",
    region_name="us-east-1"
)

chat_logs_table = dynamodb.Table(
    "chat_logs"
)

def save_chat_log(
    query_id,
    session_id,
    question,
    answer,
    sources,
    response_time
):

    chat_logs_table.put_item(

        Item={

            "query_id": query_id,

            "session_id": session_id,

            "timestamp": datetime.utcnow().isoformat(),

            "question": question,

            "answer": answer,

            "sources": sources,

            "response_time": response_time,

            "status": "success"
        }
    )