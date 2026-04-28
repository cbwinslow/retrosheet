--
— File: docs/dev/SOURCGRAPH_SETUP.md
— Purpose: Instructions for setting up Sourcegraph for code search and intelligence
— Author: Agent KiloSwift
— Date: 2026-04-27
—

# Sourcegraph Setup for Retrosheet Project

## Overview

[Sourcegraph](https://sourcegraph.com) is a self-hosted code search and navigation
platform. It enables:
- Precise code search across all repositories
- Code intelligence (go to definition, find references)
- Code review integration
- Security scanning integration

This document describes how to set up Sourcegraph locally for the Retrosheet project.

## Quick Start (Local Docker)

1. **Start Sourcegraph instance**

   ```bash
   docker-compose -f docker-compose.sourcegraph.yml up -d
   ```

2. **Access Sourcegraph**

   Open browser to: http://localhost:7080

   Default credentials: admin / admin (change immediately)

3. **Add repository**

   - Navigate to Site admin → Manage code hosts
   - Add GitHub repository: `github.com/cbwinslow/retrosheet`
   - Set clone method: Local mirror or direct clone
   - Click "Sync now"

4. **Search your code**

   Use the search bar with Cody (AI) or regex search:
   - `repo:^github\.com/cbwinslow/retrosheet$ file:\.py$ pattern:def predict`
   - `repo:github.com/cbwinslow/retrosheet type:function class:WinExpectancyCalculator`

## Advanced Configuration

### GitHub OAuth (optional)

For GitHub integration (code host connectivity):

```yaml
# In docker-compose.sourcegraph.yml, add to sourcegraph service:
environment:
  AUTH_GITHUB_CLIENT_ID: "<your-client-id>"
  AUTH_GITHUB_CLIENT_SECRET: "<your-client-secret>"
```

### Custom Storage Backends

For larger installations, configure:
- PostgreSQL with more resources
- Redis clustering
- MinIO/S3 for object storage
- GCS for cloud deployments

## CI/CD Integration

The workflow file `.github/workflows/sourcegraph-code-intel.yml` uploads
code intelligence data on every push. This enables precise navigation in
the Sourcegraph UI.

To enable:
1. Create a Sourcegraph personal access token
   - Go to https://sourcegraph.com/user/tokens
   - Create token with `code-intel-upload` scope
2. Add repository secret `SOURCGRAPH_TOKEN` in GitHub
3. Push a commit to trigger the workflow

## Usage Patterns

### Find all usages of a function

Cody prompt: "Where is get_win_expectancy called?"

Or regex:
```
repo:github.com/cbwinslow/retrosheet
path:\.py$
symbol:get_win_expectancy
```

### Search for SQL queries

```
repo:github.com/cbwinslow/retrosheet
file:\.sql$
SELECT.*FROM core\.games
```

### Code review intelligence

Push code → Sourcegraph automatically indexes → reviewers can:
- See changed symbols
- Browse impacted call sites
- Access related definitions

## Performance Notes

- Local Docker instance uses ~4GB RAM
- Initial indexing of ~1K files takes ~2-3 minutes
- Incremental updates are fast (<10s per commit)

## Alternatives

For lighter-weight needs:
- **OpenGrok**: Simpler code search
- **Livegrep**: Fast grep-style searching
- **Sourcegraph Cloud**: Hosted SaaS at sourcegraph.com (self-repo search only, upload limit 10GB)

## Documentation

- Official docs: https://docs.sourcegraph.com/
- LSG uploader: https://docs.sourcegraph.com/lsg
- Code intelligence: https://docs.sourcegraph.com/code_intelligence
