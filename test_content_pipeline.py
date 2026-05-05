#!/usr/bin/env python3
"""Simple test script for content generation pipeline."""

import sys
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Test template engine directly
try:
    from baseball.content.templates.engine import TemplateEngine
    
    print("✅ TemplateEngine import successful")
    
    # Initialize template engine
    engine = TemplateEngine()
    print("✅ TemplateEngine initialized")
    
    # List templates
    templates = engine.list_templates()
    print(f"✅ Found {len(templates)} templates: {templates}")
    
    # Validate template
    if templates:
        validation = engine.validate_template(templates[0])
        print(f"✅ Template validation: {validation}")
    
    # Test template rendering with sample data
    context = {
        'title': 'Test Game Preview',
        'game': {
            'home_team': 'Yankees',
            'away_team': 'Red Sox',
            'game_time': '7:05 PM',
            'venue': 'Yankee Stadium',
            'home_win_prob': 0.58,
            'total_runs_expected': 8.5
        }
    }
    
    if templates:
        rendered = engine.render_template(templates[0], context)
        print("✅ Template rendering successful")
        print("\n--- Rendered Content ---")
        print(rendered)
        print("--- End Content ---\n")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

# Test content generator (without LLM)
try:
    from baseball.content.llm.generator import ContentGenerator, GenerationRequest
    
    print("✅ ContentGenerator import successful")
    
    generator = ContentGenerator()
    print("✅ ContentGenerator initialized")
    
    # Create a mock request
    request = GenerationRequest(
        template_name='game-preview',
        context=context,
        content_type='game-preview'
    )
    
    print("✅ GenerationRequest created")
    
    # Test quality validation
    sample_content = "This is a test article about baseball with some numbers like 0.58 and 8.5."
    quality = generator.validate_content_quality(sample_content)
    print(f"✅ Quality validation: {quality}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n🎉 Content pipeline test completed!")
