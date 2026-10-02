from datetime import datetime, timezone
import csv
import io

from flask import Flask, request
from supabase import create_client
from google.cloud import storage

app = Flask(__name__)


# =========================
# CONFIGURATION
# =========================

SUPABASE_URL = "https://vngihvxhfpgdngmmmhip.supabase.co"
SUPABASE_KEY = "sb_publishable_OJeTNmmGmc78Nqz7aWCdNA_u7GsOqJz"

TABLE_NAME = "sales"
GCS_BUCKET = "rajeshwariflourmill-superbase-backup"

PAGE_SIZE = 1000


# =========================
# CLOUD RUN ENTRY POINT
# =========================

def main(request):
    """
    HTTP entry point for Cloud Run.
    Cloud Scheduler will call this URL.
    """

    try:
        # -------------------------
        # Connect to Supabase
        # -------------------------

        supabase = create_client(
            SUPABASE_URL,
            SUPABASE_KEY
        )

        # -------------------------
        # Read sales table
        # -------------------------

        all_rows = []
        offset = 0

        while True:

            response = (
                supabase
                .table(TABLE_NAME)
                .select("*")
                .range(
                    offset,
                    offset + PAGE_SIZE - 1
                )
                .execute()
            )

            rows = response.data or []

            if not rows:
                break

            all_rows.extend(rows)

            if len(rows) < PAGE_SIZE:
                break

            offset += PAGE_SIZE

        # -------------------------
        # Create CSV
        # -------------------------

        output = io.StringIO(
            newline=""
        )

        if all_rows:

            fieldnames = list(
                all_rows[0].keys()
            )

            writer = csv.DictWriter(
                output,
                fieldnames=fieldnames,
                extrasaction="ignore",
                lineterminator="\n"
            )

            writer.writeheader()
            writer.writerows(all_rows)

        csv_data = output.getvalue()

        output.close()

        # -------------------------
        # Backup date
        # -------------------------

        today = datetime.now(
            timezone.utc
        ).strftime("%Y-%m-%d")

        gcs_path = (
            f"{TABLE_NAME}/{today}/"
            f"{TABLE_NAME}.csv"
        )

        # -------------------------
        # Upload to GCS
        # -------------------------

        storage_client = storage.Client()

        bucket = storage_client.bucket(
            GCS_BUCKET
        )

        blob = bucket.blob(
            gcs_path
        )

        blob.upload_from_string(
            csv_data,
            content_type="text/csv"
        )

        # -------------------------
        # Success
        # -------------------------

        message = (
            f"Backup successful | "
            f"Table: {TABLE_NAME} | "
            f"Records: {len(all_rows)} | "
            f"File: gs://{GCS_BUCKET}/"
            f"{gcs_path}"
        )

        print(message)

        return message, 200

    except Exception as error:

        print(
            f"Backup failed: {error}"
        )

        return (
            f"Backup failed: {error}",
            500
        )


@app.route("/", methods=["GET", "POST"])
def run():
    return main(request)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)