import os
from datetime import datetime, timedelta


def delete_old_files(folder_path):
    # Calculate the date 7 days ago
    seven_days_ago = datetime.now() - timedelta(days=7)

    # Loop through files in the folder and delete old files
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        file_creation_time = datetime.fromtimestamp(
            os.path.getctime(file_path))

        if file_creation_time < seven_days_ago:
            os.remove(file_path)
            print(f"Removed {filename}")


if __name__ == "__main__":
    # Manually specify the folder path
    folder_path = '/var/www/BKBC/static/card_storage/'
    delete_old_files(folder_path)
