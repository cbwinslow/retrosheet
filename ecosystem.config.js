/**
 * PM2 Ecosystem Configuration for MLB Live Server
 *
 * Usage:
 *   pm2 start ecosystem.config.js
 *   pm2 save
 *   pm2 startup
 *
 * For more options: https://pm2.keymetrics.io/docs/usage/application-declaration/
 */

module.exports = {
  apps: [
    {
      name: 'mlb-live-server',
      script: 'python',
      args: '-m mlb_predict.streaming.server',
      cwd: '/opt/retrosheet',

      // Environment variables
      env: {
        NODE_ENV: 'production',
        PYTHONPATH: '/opt/retrosheet',
        PGHOST: 'localhost',
        PGPORT: '5432',
        PGDATABASE: 'retrosheet',
        PGUSER: 'mlb',
        LOG_LEVEL: 'INFO',
        WEBSOCKET_HOST: '0.0.0.0',
        WEBSOCKET_PORT: '8765',
        CACHE_TTL: '5',
        POLL_INTERVAL: '10',
        MAX_CLIENTS: '1000',
        MAX_CACHE_SIZE: '10000',
      },

      // Environment-specific variables (use --env production)
      env_production: {
        NODE_ENV: 'production',
        LOG_LEVEL: 'WARNING',
      },
      env_development: {
        NODE_ENV: 'development',
        LOG_LEVEL: 'DEBUG',
      },

      // Process management
      instances: 1,
      exec_mode: 'fork',

      // Auto-restart
      autorestart: true,
      restart_delay: 5000,
      max_restarts: 10,
      min_uptime: '10s',

      // Memory management
      max_memory_restart: '512M',

      // Logging
      log_file: '/var/log/mlb-live-server/combined.log',
      out_file: '/var/log/mlb-live-server/out.log',
      error_file: '/var/log/mlb-live-server/error.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      merge_logs: true,

      // Monitoring
      monitor: true,

      // Source map (for error tracing)
      source_map_support: false,

      // Kill timeout
      kill_timeout: 5000,

      // Listen timeout
      listen_timeout: 10000,

      // Shutdown with message
      shutdown_with_message: true,

      // Wait ready
      wait_ready: true,

      // Max restarts threshold
      max_restarts_threshold: 3,
    },

    // Optional: Dashboard static file server
    {
      name: 'mlb-dashboard',
      script: 'python',
      args: '-m http.server 8080 --directory /opt/retrosheet/dashboard',
      cwd: '/opt/retrosheet',

      env: {
        NODE_ENV: 'production',
      },

      instances: 1,
      autorestart: true,
      max_memory_restart: '128M',

      log_file: '/var/log/mlb-dashboard/combined.log',
      out_file: '/var/log/mlb-dashboard/out.log',
      error_file: '/var/log/mlb-dashboard/error.log',
    },
  ],

  // Deployment configuration (if using PM2 deploy)
  deploy: {
    production: {
      user: 'mlb',
      host: ['cloudcurio.cc', 'www.cloudcurio.cc', 'predictions.cloudcurio.cc'],
      ref: 'origin/main',
      repo: 'git@github.com:cbwinslow/retrosheet.git',
      path: '/opt/retrosheet',
      'post-deploy':
        'pip install -r requirements.txt && pm2 reload ecosystem.config.js --env production',
      'pre-setup': 'apt-get install -y python3-pip postgresql-client',
    },
  },
}