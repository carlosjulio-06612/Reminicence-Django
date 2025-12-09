import os
import sys
import django

sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "BK_Reminicence.settings.local")
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    print("Attempting to add column updated_at to forum_posts...")
    try:
        # Check if column already exists
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'forum_posts' AND column_name = 'updated_at'")
        if cursor.fetchone():
            print("Column updated_at already exists.")
        else:
            # Add the column
            # Note: We need to handle the default. auto_now=True usually implies a default of current timestamp.
            cursor.execute('ALTER TABLE "forum_posts" ADD COLUMN "updated_at" timestamp with time zone DEFAULT NOW();')
            # Update existing rows to have the current time (already done by DEFAULT NOW())
            # Remove the default if we want strictly Django behavior (Django usually creates it with a default then drops it? Or keeps it?)
            # For now, keeping DEFAULT NOW() is safer for integrity.
            print("Successfully added updated_at column.")
    except Exception as e:
        print(f"Error: {e}")
