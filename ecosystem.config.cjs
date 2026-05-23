/**
 * PM2 process config for EC2 production.
 * Usage (on server): cd ~/e-Patrolling && pm2 start ecosystem.config.cjs
 */
module.exports = {
  apps: [
    {
      name: 'backend',
      cwd: './backend',
      script: '../.venv/bin/uvicorn',
      args: 'main:app --host 0.0.0.0 --port 5000',
      interpreter: 'none',
      env: {
        ENVIRONMENT: 'production',
      },
      max_restarts: 10,
      restart_delay: 3000,
    },
  ],
}
