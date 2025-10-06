"""
Lambda handler: GET /analyze/{jobId}/export
CSVエクスポート
"""
import csv
import io
import json
import os
from typing import Dict

import boto3

dynamodb = boto3.resource('dynamodb')

TABLE_NAME = os.environ['DYNAMODB_TABLE_JOBS']
CORS_ORIGIN = os.environ.get('CORS_ORIGIN', '*')


def lambda_handler(event: Dict, context) -> Dict:
    """
    GET /analyze/{jobId}/export のハンドラー
    """
    headers = {
        'Content-Type': 'text/csv; charset=utf-8',
        'Access-Control-Allow-Origin': CORS_ORIGIN,
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'GET,OPTIONS',
        'Content-Disposition': 'attachment; filename="comments.csv"'
    }
    
    if event.get('httpMethod') == 'OPTIONS':
        return {'statusCode': 200, 'headers': headers, 'body': ''}
    
    try:
        job_id = event.get('pathParameters', {}).get('jobId')
        
        if not job_id:
            headers['Content-Type'] = 'application/json'
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'validation_error', 'message': 'jobId is required'})
            }
        
        # DynamoDBから取得
        table = dynamodb.Table(TABLE_NAME)
        response = table.get_item(Key={'jobId': job_id})
        
        if 'Item' not in response:
            headers['Content-Type'] = 'application/json'
            return {
                'statusCode': 404,
                'headers': headers,
                'body': json.dumps({'error': 'not_found', 'message': 'Job not found'})
            }
        
        item = response['Item']
        
        if item['status'] != 'completed' or 'result' not in item:
            headers['Content-Type'] = 'application/json'
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'not_ready', 'message': 'Job not completed yet'})
            }
        
        # CSV生成
        output = io.StringIO()
        writer = csv.writer(output)
        
        # ヘッダー
        writer.writerow([
            'commentId', 'authorDisplayName', 'textClean', 
            'sentimentLabel', 'sentimentScore', 'sentimentReason',
            'likeCount', 'publishedAt', 'isReply'
        ])
        
        # データ行
        comments = item['result'].get('comments', [])
        for comment in comments:
            writer.writerow([
                comment.get('commentId', ''),
                comment.get('authorDisplayName', ''),
                comment.get('textClean', ''),
                comment.get('sentimentLabel', ''),
                comment.get('sentimentScore', 0),
                comment.get('sentimentReason', ''),
                comment.get('likeCount', 0),
                comment.get('publishedAt', ''),
                comment.get('isReply', False)
            ])
        
        csv_content = output.getvalue()
        output.close()
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': csv_content
        }
    
    except Exception as e:
        print(f"Error: {str(e)}")
        headers['Content-Type'] = 'application/json'
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': 'internal_error', 'message': str(e)})
        }

