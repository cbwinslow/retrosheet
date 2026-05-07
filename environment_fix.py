#!/usr/bin/env python3
"""
Environment Fix Script
Resolves common environment and configuration issues
"""

import os
import sys
import json
import subprocess
from pathlib import Path

def fix_mcp_configuration():
    """Fix MCP configuration issues"""
    print("🔧 Fixing MCP configuration...")
    
    mcp_config_path = Path(".ai/mcp/mcp.json")
    if not mcp_config_path.exists():
        print("❌ MCP config not found")
        return False
    
    # Load current config
    with open(mcp_config_path, 'r') as f:
        config = json.load(f)
    
    # Update GitHub configuration
    if 'github' not in config:
        config['github'] = {}
    
    config['github']['token'] = os.getenv('GITHUB_TOKEN', '')
    config['github']['api_url'] = 'https://api.github.com'
    
    # Save updated config
    with open(mcp_config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    print("✅ MCP configuration updated")
    return True

def fix_plugin_system():
    """Fix plugin system issues"""
    print("🔧 Fixing plugin system...")
    
    # Ensure baseball package is properly installed
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-e", "."], check=True)
        print("✅ Baseball package installed in development mode")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install baseball package: {e}")
        return False
    
    return True

def fix_core_exports():
    """Fix core module exports"""
    print("🔧 Fixing core module exports...")
    
    core_init_path = Path("baseball/core/__init__.py")
    if not core_init_path.exists():
        print("❌ Core __init__.py not found")
        return False
    
    # Read current content
    with open(core_init_path, 'r') as f:
        content = f.read()
    
    # Check if all required exports are present
    required_exports = [
        'ErrorArchitecture',
        'IntelligentRecovery',
        'SystemMonitoring',
        'PluginSystem',
        'IntegrationLayer'
    ]
    
    missing_exports = [export for export in required_exports if export not in content]
    if missing_exports:
        print(f"❌ Missing exports: {missing_exports}")
        return False
    
    print("✅ Core module exports verified")
    return True

def verify_environment():
    """Verify environment is properly configured"""
    print("🔧 Verifying environment...")
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required")
        return False
    
    # Check required environment variables
    required_vars = ['GITHUB_TOKEN']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        print(f"❌ Missing environment variables: {missing_vars}")
        return False
    
    # Check baseball package imports
    try:
        import baseball
        print("✅ Baseball package imports successfully")
    except ImportError as e:
        print(f"❌ Failed to import baseball package: {e}")
        return False
    
    return True

def main():
    """Main environment fix function"""
    print("🚀 Starting environment fix...")
    
    fixes = [
        fix_mcp_configuration,
        fix_plugin_system,
        fix_core_exports,
        verify_environment
    ]
    
    all_success = True
    for fix in fixes:
        if not fix():
            all_success = False
            print("❌ Fix failed")
        else:
            print("✅ Fix successful")
        print()
    
    if all_success:
        print("🎉 All environment fixes completed successfully!")
    else:
        print("❌ Some fixes failed. Please check the errors above.")
    
    return all_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
