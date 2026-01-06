import os

def load_template(path: str) -> str:
    """Load a template file from the templates directory."""
    # Now in utils/ui, so need to go up two levels to root
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    full_path = os.path.join(base_dir, "templates", path)
    
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"<!-- Template Error: {str(e)} -->"
