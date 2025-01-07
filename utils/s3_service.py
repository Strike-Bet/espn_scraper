import json
from datetime import datetime
from typing import Union, BinaryIO
import os 
import dotenv
import logging


import boto3
from botocore.exceptions import ClientError

dotenv.load_dotenv()


logger = logging.getLogger(__name__)


class S3Service:
    """Service class for handling AWS S3 operations"""

    def __init__(self):
        """Initialize S3 client with credentials from Django settings"""
        self.client = boto3.client(
            "s3",
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name="us-east-1",
        )
        self.bucket = os.getenv("AWS_BUCKET_NAME")

    def upload_file(
        self,
        file_data: Union[str, bytes, BinaryIO],
        s3_path: str,
        content_type: str = "application/json",
    ) -> bool:
        """
        Upload a file to S3

        Args:
            file_data: The data to upload (string, bytes, or file-like object)
            s3_path: The path/key in S3 where the file should be stored
            content_type: The MIME type of the file

        Returns:
            bool: True if upload was successful, False otherwise
        """
        try:
            # If file_data is a string, convert to bytes
            if isinstance(file_data, str):
                file_data = file_data.encode("utf-8")

            # Upload to S3
            self.client.put_object(
                Bucket=self.bucket,
                Key=s3_path,
                Body=file_data,
                ContentType=content_type,
            )

            logger.info(f"Successfully uploaded to s3://{self.bucket}/{s3_path}")
            return True

        except ClientError as e:
            logger.error(f"Failed to upload to S3: {str(e)}")
            return False

    def download_file(self, s3_path: str) -> Union[dict, None]:
        """
        Download a JSON file from S3

        Args:
            s3_path: The path/key in S3 where the file is stored

        Returns:
            dict: The JSON data if successful, None if failed
        """
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=s3_path)
            file_content = response["Body"].read().decode("utf-8")
            return json.loads(file_content)

        except ClientError as e:
            logger.error(f"Failed to download from S3: {str(e)}")
            return None


def upload_to_s3(
    data: Union[str, dict], s3_path: str, include_timestamp: bool = True
) -> bool:
    """
    Helper function to upload data to S3

    Args:
        data: The data to upload (string or dict)
        s3_path: The base path in S3
        include_timestamp: Whether to include timestamp in filename

    Returns:
        bool: True if upload was successful, False otherwise
    """
    s3_service = S3Service()

    # If data is a dict, convert to JSON string
    if isinstance(data, dict):
        data = json.dumps(data, indent=2)

    # Add timestamp to path if requested
    if include_timestamp:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        path_parts = s3_path.rsplit(".", 1)
        s3_path = f"{path_parts[0]}_{timestamp}.{path_parts[1]}"
        print('s3_path', s3_path)

    try:
        s3_service.upload_file(data, s3_path)
    except Exception as e:
        print(f"Error uploading to s3: {e}")
        return False
    return True