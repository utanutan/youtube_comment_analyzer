"""
Lambda handler: POST /analyze
ジョブを作成してSQSキューに投入
"""
import json
import os
import time
import uuid
from typing import Dict

import boto3

dynamodb = boto3.resource('dynamodb')
sqs = boto3.client('sqs')

TABLE_NAME = os.environ['DYNAMODB_TABLE_JOBS']
SQS_QUEUE_URL = os.environ['SQS_QUEUE_URL']
CORS_ORIGIN = os.environ.get('CORS_ORIGIN', '*')


def lambda_handler(event: Dict, context) -> Dict:
    """
    POST /analyze のハンドラー
    """
    # CORS headers
    headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': CORS_ORIGIN,
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'POST,OPTIONS'
    }
    
    # OPTIONS request (CORS preflight)
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': headers,
            'body': ''
        }
    
    try:
        # リクエストボディ解析
        body = json.loads(event.get('body', '{}'))
        video_id = body.get('videoId', '').strip()
        max_comments = min(int(body.get('maxComments', 500)), 5000)
        lang = body.get('lang', 'ja')
        
        # バリデーション
        if not video_id or len(video_id) != 11:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({
                    'error': 'validation_error',
                    'message': 'Invalid videoId. Must be 11 characters.'
                })
            }
        
        # ジョブID生成
        job_id = str(uuid.uuid4())
        timestamp = int(time.time())
        ttl = timestamp + (7 * 24 * 3600)  # 7日後に自動削除
        
        # DynamoDBにジョブ登録
        table = dynamodb.Table(TABLE_NAME)
        table.put_item(
            Item={
                'jobId': job_id,
                'videoId': video_id,
                'status': 'queued',
                'createdAt': timestamp,
                'updatedAt': timestamp,
                'ttl': ttl,
                'params': {
                    'maxComments': max_comments,
                    'lang': lang
                },
                'progress': {
                    'fetched': 0,
                    'analyzed': 0,
                    'total': 0
                }
            }
        )
        
        # SQSキューにジョブ投入
        sqs.send_message(
            QueueUrl=SQS_QUEUE_URL,
            MessageBody=json.dumps({
                'jobId': job_id,
                'videoId': video_id,
                'maxComments': max_comments,
                'lang': lang
            })
        )
        
        # 202 Accepted レスポンス
        return {
            'statusCode': 202,
            'headers': headers,
            'body': json.dumps({
                'jobId': job_id,
                'status': 'queued',
                'createdAt': timestamp
            })
        }
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({
                'error': 'internal_error',
                'message': str(e)
            })
        }

