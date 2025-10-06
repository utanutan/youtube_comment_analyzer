"""
Lambda handler: GET /analyze/{jobId}
ジョブのステータスと結果を取得
"""
import json
import os
from typing import Dict

import boto3
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource('dynamodb')

TABLE_NAME = os.environ['DYNAMODB_TABLE_JOBS']
CORS_ORIGIN = os.environ.get('CORS_ORIGIN', '*')


def lambda_handler(event: Dict, context) -> Dict:
    """
    GET /analyze/{jobId} のハンドラー
    """
    headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': CORS_ORIGIN,
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'GET,OPTIONS'
    }
    
    if event.get('httpMethod') == 'OPTIONS':
        return {'statusCode': 200, 'headers': headers, 'body': ''}
    
    try:
        # パスパラメータ取得
        job_id = event.get('pathParameters', {}).get('jobId')
        
        if not job_id:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'validation_error', 'message': 'jobId is required'})
            }
        
        # DynamoDBから取得
        table = dynamodb.Table(TABLE_NAME)
        response = table.get_item(Key={'jobId': job_id})
        
        if 'Item' not in response:
            return {
                'statusCode': 404,
                'headers': headers,
                'body': json.dumps({'error': 'not_found', 'message': 'Job not found'})
            }
        
        item = response['Item']
        
        # レスポンス構築
        result = {
            'jobId': item['jobId'],
            'videoId': item['videoId'],
            'status': item['status'],
            'createdAt': item['createdAt'],
            'updatedAt': item['updatedAt'],
            'progress': item.get('progress', {}),
        }
        
        # 完了時は結果も含める
        if item['status'] == 'completed' and 'result' in item:
            result['result'] = item['result']
        
        # 失敗時はエラー情報
        if item['status'] == 'failed' and 'error' in item:
            result['error'] = item['error']
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(result, ensure_ascii=False)
        }
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': 'internal_error', 'message': str(e)})
        }

