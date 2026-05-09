# MCP Troubleshooting Guide

## Overview
This document provides troubleshooting steps for MCP (Model Context Protocol) server issues.

## Common Issues

### 1. Server Connection Problems

Check if MCP server is running, verify configuration in Windsurf settings, and ensure proper authentication tokens are set.

### 2. MCP Configuration Format

The Windsurf MCP config should look like this:

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_TOKEN": "YOUR_GITHUB_TOKEN_HERE"
      }
    }
  }
}
```

### 3. Installation Steps

```bash
# Install MCP server globally
npm install -g @modelcontextprotocol/server-github

# Or use npx directly
npx -y @modelcontextprotocol/server-github
```

### 4. Debugging Commands

```bash
# Check MCP server status
npx @modelcontextprotocol/server-github --help

# Test connection
curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/user
```

### 5. Common Error Messages

- **Authentication failed**: Check token validity
- **Server not found**: Verify server URL and network connectivity
- **Permission denied**: Ensure token has required scopes

## Resources

- [MCP Documentation](https://modelcontextprotocol.io/)
- [GitHub MCP Server](https://github.com/modelcontextprotocol/servers)