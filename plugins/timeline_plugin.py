"""
timeline_plugin.py - Plugin obsługujący akcję TIME LINE z panelu ikon.
Funkcja `show_timeline(card)` wyświetla dialog historii (TimelineDialog).
"""


def is_available():
    return True


def show_timeline(card):
    try:
        from modules.ui.dialogs import TimelineDialog
        scene = card.scene() if hasattr(card, 'scene') else None
        pm = scene.password_manager if scene and hasattr(scene, 'password_manager') else None
        dialog = TimelineDialog(card.history_text, card=card, password_manager=pm)
        dialog.exec()
    except Exception as e:
        # Re-raise so caller can fallback
        raise
