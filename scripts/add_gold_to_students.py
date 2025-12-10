"""
Script to add 500 gold to all characters in the database.
This updates the Character model's gold field, which is the active gold used in gameplay.
"""
import sys
import os

# Add the parent directory to the path so we can import app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models import db
from app.models.character import Character

app = create_app()
with app.app_context():
    # Get all characters
    characters = Character.query.all()
    
    if not characters:
        print("No characters found in the database.")
    else:
        updated_count = 0
        for character in characters:
            character.gold += 500
            updated_count += 1
        
        db.session.commit()
        print(f"Successfully added 500 gold to {updated_count} character(s).")
        
        # Show summary
        total_gold = sum(c.gold for c in Character.query.all())
        print(f"Total gold across all characters: {total_gold}")

