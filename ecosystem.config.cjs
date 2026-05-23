/**
 * PM2 process config for EC2 production.
 * Usage: cd ~/e-Patrolling && pm2 start ecosystem.config.cjs
 */
module.exports = {
  apps: [
    {
      name: 'backend',
      cwd: '.',
      script: './scripts/start-backend.sh',
      interpreter: 'bash',
      env: {
        ENVIRONMENT: 'production',
      },
      max_restarts: 15,
      restart_delay: 5000,
      error_file: './storage/logs/pm2-backend-error.log',
      out_file: './storage/logs/pm2-backend-out.log',
    },
  ],
}
