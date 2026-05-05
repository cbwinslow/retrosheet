"""
Template Engine for Content Generation

Jinja2-based template rendering system for baseball analysis articles.
Handles dynamic content insertion from model predictions and data sources.
"""

from jinja2 import Environment, FileSystemLoader, Template, TemplateError
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class TemplateEngine:
    """Template rendering engine for baseball content generation."""
    
    def __init__(self, template_dir: Optional[str] = None):
        """Initialize template engine with template directory."""
        if template_dir is None:
            template_path = Path(__file__).parent.parent.parent.parent / "templates" / "content"
        else:
            template_path = Path(template_dir)
        
        self.template_dir = template_path
        self.template_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=True,
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # Add custom filters
        self._add_custom_filters()
        
        logger.info(f"Template engine initialized with directory: {self.template_dir}")
    
    def _add_custom_filters(self):
        """Add custom Jinja2 filters for baseball content."""
        
        def format_percentage(value: float) -> str:
            """Format decimal as percentage."""
            if value is None:
                return "N/A"
            return f"{value * 100:.1f}%"
        
        def format_odds(value: float) -> str:
            """Format decimal as American odds."""
            if value is None:
                return "N/A"
            if value >= 0.5:
                return f"+{int((value / (1 - value)) * 100)}"
            else:
                return f"{int(-100 / (value / (1 - value)))}"
        
        def format_number(value: Any) -> str:
            """Format numbers with commas."""
            if value is None:
                return "N/A"
            if isinstance(value, (int, float)):
                return f"{value:,.0f}" if isinstance(value, int) else f"{value:,.2f}"
            return str(value)
        
        def date_format(value: datetime, format_str: str = "%B %d, %Y") -> str:
            """Format datetime object."""
            if value is None:
                return "N/A"
            return value.strftime(format_str)
        
        # Register filters
        self.env.filters['percentage'] = format_percentage
        self.env.filters['odds'] = format_odds
        self.env.filters['number'] = format_number
        self.env.filters['date'] = date_format
    
    def render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """
        Render a template with the given context.
        
        Args:
            template_name: Name of the template file
            context: Dictionary of variables for template rendering
            
        Returns:
            Rendered content as string
            
        Raises:
            TemplateError: If template rendering fails
        """
        try:
            template = self.env.get_template(template_name)
            rendered = template.render(**context)
            logger.info(f"Successfully rendered template: {template_name}")
            return rendered
        except TemplateError as e:
            logger.error(f"Template rendering failed for {template_name}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error rendering {template_name}: {e}")
            raise TemplateError(f"Failed to render template {template_name}: {e}")
    
    def create_template(self, name: str, content: str) -> None:
        """
        Create a new template file.
        
        Args:
            name: Template filename
            content: Template content
        """
        template_path = self.template_dir / name
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.info(f"Created template: {template_path}")
    
    def list_templates(self) -> List[str]:
        """List all available template files."""
        templates = []
        for file_path in self.template_dir.glob("*.j2"):
            templates.append(file_path.name)
        return sorted(templates)
    
    def validate_template(self, template_name: str) -> dict[str, Any]:
        """
        Validate a template syntax and extract variables.
        
        Args:
            template_name: Name of template to validate
            
        Returns:
            Validation result with variables and syntax check
        """
        try:
            template = self.env.get_template(template_name)
            environment = template.environment
            loader = environment.loader
            
            if loader is None:
                raise ValueError("Template loader not found")
            
            # Extract variables from template
            from jinja2 import meta
            template_source = loader.get_source(environment, template_name)[0]
            ast = environment.parse(template_source)
            variables = meta.find_undeclared_variables(ast)
            
            return {
                'valid': True,
                'variables': list(variables),
                'error': None
            }
        except Exception as e:
            return {
                'valid': False,
                'variables': [],
                'error': str(e)
            }
    
    def get_template_info(self, template_name: str) -> Dict[str, Any]:
        """
        Get detailed information about a template.
        
        Args:
            template_name: Name of template
            
        Returns:
            Template metadata
        """
        template_path = self.template_dir / template_name
        
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_name}")
        
        # Get file stats
        stat = template_path.stat()
        
        # Validate and extract variables
        validation = self.validate_template(template_name)
        
        return {
            'name': template_name,
            'path': str(template_path),
            'size': stat.st_size,
            'created': datetime.fromtimestamp(stat.st_ctime),
            'modified': datetime.fromtimestamp(stat.st_mtime),
            'variables': validation['variables'],
            'valid': validation['valid'],
            'error': validation['error']
        }
