import boto3
import json

bedrock = boto3.client(
    "bedrock-runtime",
    region_name="us-east-1"
)

def get_embedding(text):

    response = bedrock.invoke_model(

        modelId="amazon.titan-embed-text-v2:0",

        body=json.dumps({
            "inputText": text
        })
    )

    response_body = json.loads(
        response['body'].read()
    )

    return response_body['embedding']