import os
import sys
import django

sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "BK_Reminicence.settings.local")
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("SHOW search_path")
    search_path = cursor.fetchone()[0]
    print(f"Current search_path: {search_path}")
    
    # List all tables in the current schema (first one in search path)
    # usually search_path is "schema, public"
    main_schema = search_path.split(',')[0].strip()
    print(f"Checking schema: {main_schema}")
    
    cursor.execute(f"SELECT table_name FROM information_schema.tables WHERE table_schema = '{main_schema}'")
    tables = [row[0] for row in cursor.fetchall()]
    print("Tables found:", tables)
    
    if 'forum_topics' in tables:
        print("forum_topics exists.")
    else:
        print("forum_topics MISSING.")
        
    if 'forum_posts' in tables:
        print("forum_posts exists.")
    else:
        print("forum_posts MISSING.")
