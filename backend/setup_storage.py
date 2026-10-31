import os
from contextlib import closing

from botocore.exceptions import BotoCoreError, ClientError

from app.storage import get_storage_client


def main():
    try:
        bucket = os.environ["S3_BUCKET"]
        with closing(get_storage_client()) as client:
            try:
                client.head_bucket(Bucket=bucket)
            except ClientError as error:
                if error.response["ResponseMetadata"]["HTTPStatusCode"] != 404:
                    raise
                client.create_bucket(Bucket=bucket)
    except (BotoCoreError, ClientError, KeyError):
        raise SystemExit("Storage setup failed. Check the service and local S3 settings.") from None
    print(f"Bucket ready: {bucket}")


if __name__ == "__main__":
    main()
