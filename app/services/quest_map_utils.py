from app.models.quest import QuestLog
from sqlalchemy.orm import Session

def find_available_coordinates(character_id, session: Session, grid_width=10, grid_height=10):
    """
    Find the first available (x, y) coordinate for a character's quest map.
    Scans left-to-right, top-to-bottom. Returns (x, y) or raises ValueError if full.
    """
    # Query all occupied coordinates for this character
    occupied = set(
        (log.x_coordinate, log.y_coordinate)
        for log in session.query(QuestLog)
            .filter_by(character_id=character_id)
            .filter(QuestLog.x_coordinate != None, QuestLog.y_coordinate != None)
            .all()
    )
    for y in range(grid_height):
        for x in range(grid_width):
            if (x, y) not in occupied:
                return x, y
    raise ValueError(f"No available coordinates on the {grid_width}x{grid_height} map for character {character_id}") 