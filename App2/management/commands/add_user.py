import csv
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Create user accounts from a CSV file'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to the CSV file')

    def handle(self, *args, **kwargs):
        csv_file = kwargs['csv_file']
        with open(csv_file, 'r') as file:
            ctr = 0
            reader = csv.DictReader(file)
            for row in reader:
                ctr += 1
                username = row['Username']
                password = row['Password']
                first_name = row['Name']
                email = row['Email ID']
                # Check if username already exists
                if not User.objects.filter(username=username).exists():
                    # Create user
                    user = User.objects.create_user(username=username, password=password, email=email, first_name=first_name)
                    self.stdout.write(self.style.SUCCESS(f"{ctr} --> User {username} created successfully."))
                else:
                    self.stdout.write(self.style.WARNING(f"{ctr} --> User {username} already exists."))
