import os
from jinja2 import Environment, FileSystemLoader, select_autoescape

# Initialize Jinja2 environment
template_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "templates")
jinja_env = Environment(
    loader=FileSystemLoader(template_dir),
    autoescape=select_autoescape(['html', 'xml'])
)

def load_template(path: str, **kwargs) -> str:
    """
    Load and render a template using Jinja2.
    Supports template inheritance (e.g., {% extends 'base.html' %}).
    """
    try:
        template = jinja_env.get_template(path)
        return template.render(**kwargs)
    except Exception as e:
        # Fallback to simple file read if Jinja fails or file not found in loader
        try:
            full_path = os.path.join(template_dir, path)
            if os.path.exists(full_path):
                with open(full_path, "r", encoding="utf-8") as f:
                    return f.read()
            return f"<!-- Template Error: {str(e)} -->"
        except Exception:
            return f"<!-- Template Error: {str(e)} -->"
