import os
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging
import json

try:
    import boto3
except ImportError:
    boto3 = None

logger = logging.getLogger(__name__)

class PrivacyCompliantStorage:
    """Storage manager with GDPR compliance and auto-cleanup"""

    def __init__(self):
        self.storage_backend = os.getenv('STORAGE_BACKEND', 'local')
        self.retention_days = int(os.getenv('RETENTION_DAYS', '7'))
        self.s3_client = None

        if self.storage_backend == 's3':
            if boto3 is None:
                raise ImportError("boto3 is required for S3 storage backend")
            self.s3_client = boto3.client('s3')
            self.bucket_name = os.getenv('S3_BUCKET', 'agentos-temp')

    def store_clip(self, clip_data: bytes, job_id: str, clip_id: str, ttl_days: int = 7) -> Dict[str, Any]:
        """Store clip with automatic expiration"""

        storage_key = f'clips/{job_id}/{clip_id}.mp4'
        expires_at = datetime.now() + timedelta(days=ttl_days)

        if self.storage_backend == 's3':
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=storage_key,
                Body=clip_data,
                Metadata={
                    'expires': expires_at.isoformat(),
                    'auto-delete': 'true',
                    'job-id': job_id
                },
                StorageClass='STANDARD_IA'
            )

            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': storage_key},
                ExpiresIn=ttl_days * 24 * 3600
            )

            return {
                'storage_type': 's3',
                'storage_key': storage_key,
                'url': url,
                'expires_at': expires_at,
                'size_bytes': len(clip_data)
            }

        else:
            # Local temporary storage
            temp_dir = f'/tmp/agentos/clips/{job_id}'
            os.makedirs(temp_dir, exist_ok=True)

            file_path = f'{temp_dir}/{clip_id}.mp4'
            with open(file_path, 'wb') as f:
                f.write(clip_data)

            return {
                'storage_type': 'local',
                'storage_key': file_path,
                'url': f'/api/clips/temp/{job_id}/{clip_id}',
                'expires_at': expires_at,
                'size_bytes': len(clip_data)
            }

    def delete_job_content(self, job_id: str) -> bool:
        """Delete all content for a job (GDPR compliance)"""

        try:
            if self.storage_backend == 's3':
                response = self.s3_client.list_objects_v2(
                    Bucket=self.bucket_name,
                    Prefix=f'clips/{job_id}/'
                )

                if 'Contents' in response:
                    objects = [{'Key': obj['Key']} for obj in response['Contents']]
                    self.s3_client.delete_objects(
                        Bucket=self.bucket_name,
                        Delete={'Objects': objects}
                    )
            else:
                import shutil
                temp_dir = f'/tmp/agentos/clips/{job_id}'
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)

            logger.info(f'Deleted all content for job {job_id}')
            return True

        except Exception as e:
            logger.error(f'Failed to delete job content: {e}')
            return False

    def extract_marketing_insights(self, job_data: Dict) -> Dict[str, Any]:
        """Extract anonymous marketing insights before deletion"""

        return {
            'content_fingerprint': hashlib.sha256(job_data['video_url'].encode()).hexdigest(),
            'content_category': job_data.get('content_type', 'unknown'),
            'viral_score': job_data.get('viral_score'),
            'engagement_score': job_data.get('engagement_score'),
            'detected_trends': job_data.get('keywords', []),
            'region': self._get_region_from_request(),
            'device_category': self._get_device_category(),
            'processed_date': datetime.now().date()
        }

    def _get_region_from_request(self) -> str:
        return os.getenv('DEFAULT_REGION', 'NL')

    def _get_device_category(self) -> str:
        return 'web'