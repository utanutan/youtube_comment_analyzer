"""
Lambda handler: SQS トリガー
YouTube取得 + OpenAI分析の非同期処理
"""
import json
import os
import time
from typing import Dict

import boto3

from openai_sentiment import OpenAISentimentAnalyzer
from youtube_analyzer import analyze_comments, fetch_comments

dynamodb = boto3.resource('dynamodb')

TABLE_NAME = os.environ['DYNAMODB_TABLE_JOBS']
YT_API_KEY = os.environ['YT_API_KEY']
OPENAI_API_KEY = os.environ['OPENAI_API_KEY']


def update_job_status(job_id: str, updates: Dict):
    """DynamoDBのジョブ情報を更新"""
    table = dynamodb.Table(TABLE_NAME)
    
    update_expr_parts = []
    expr_attr_values = {}
    
    for key, value in updates.items():
        update_expr_parts.append(f"{key} = :{key}")
        expr_attr_values[f":{key}"] = value
    
    # updatedAtを自動更新
    update_expr_parts.append("updatedAt = :updatedAt")
    expr_attr_values[":updatedAt"] = int(time.time())
    
    update_expr = "SET " + ", ".join(update_expr_parts)
    
    table.update_item(
        Key={'jobId': job_id},
        UpdateExpression=update_expr,
        ExpressionAttributeValues=expr_attr_values
    )


def lambda_handler(event: Dict, context) -> Dict:
    """
    SQSトリガーのハンドラー
    """
    print(f"Processing {len(event['Records'])} record(s)")
    
    for record in event['Records']:
        try:
            # SQSメッセージ解析
            message = json.loads(record['body'])
            job_id = message['jobId']
            video_id = message['videoId']
            max_comments = message.get('maxComments', 500)
            lang = message.get('lang', 'ja')
            
            print(f"Processing job {job_id} for video {video_id}")
            
            # ステータス更新: running
            update_job_status(job_id, {'status': 'running'})
            
            # YouTube コメント取得
            def progress_callback(msg):
                print(msg)
            
            comments = fetch_comments(
                api_key=YT_API_KEY,
                video_id=video_id,
                max_comments=max_comments,
                include_replies=True,
                progress_callback=progress_callback
            )
            
            # 進捗更新
            update_job_status(job_id, {
                'progress': {
                    'fetched': len(comments),
                    'analyzed': 0,
                    'total': len(comments)
                }
            })
            
            # OpenAI 感情分析
            analyzer = OpenAISentimentAnalyzer(
                api_key=OPENAI_API_KEY,
                model='gpt-4o-mini',
                batch_size=20
            )
            
            texts = [c.get('textOriginal', '') for c in comments]
            sentiments = analyzer.analyze_batch(texts, progress_callback=progress_callback)
            
            # 感情結果をマージ
            def sentiment_analyzer_func(text):
                idx = texts.index(text) if text in texts else 0
                return sentiments[idx] if idx < len(sentiments) else {
                    'label': 'neutral', 'score': 0.0, 'reason': ''
                }
            
            # 分析実行
            analysis = analyze_comments(comments, sentiment_analyzer_func)
            
            # 結果保存
            update_job_status(job_id, {
                'status': 'completed',
                'progress': {
                    'fetched': len(comments),
                    'analyzed': len(comments),
                    'total': len(comments)
                },
                'result': analysis
            })
            
            print(f"Job {job_id} completed successfully")
        
        except Exception as e:
            print(f"Error processing job {job_id}: {str(e)}")
            
            # エラー状態を保存
            try:
                update_job_status(job_id, {
                    'status': 'failed',
                    'error': {
                        'code': 'processing_error',
                        'message': str(e)
                    }
                })
            except:
                pass
            
            # SQS DLQ に送るため例外を再スロー
            raise
    
    return {'statusCode': 200, 'body': 'Processed'}

