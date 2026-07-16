/**
 * PM2 process config for Shakti / e-Patrolling (Hostinger VPS / EC2).
 * Usage: cd ~/e-Patrolling && pm2 start ecosystem.config.cjs
 *
 * Port map on shared Hostinger VPS (do not use CapStack's :3000):
 *   80/443  — nginx
 *   3000    — CapStack (separate project; leave alone)
 *   5100    — Shakti/e-Patrolling API (this app)
 *   8090    — TravelCRM edge (docker)
 *   19119   — Hermes agent (docker)
 */
module.exports = {
  apps: [
    {
      name: 'shakti-backend',
      cwd: '.',
      script: './scripts/start-backend.sh',
      interpreter: 'bash',
      env: {
        ENVIRONMENT: 'production',
        BACKEND_PORT: '5100',
        // Ubuntu 26.04: Playwright has no chromium build for ubuntu26.04-x64 yet
        PLAYWRIGHT_HOST_PLATFORM_OVERRIDE: 'ubuntu24.04-x64',
      },
      max_restarts: 15,
      restart_delay: 5000,
      error_file: './storage/logs/pm2-backend-error.log',
      out_file: './storage/logs/pm2-backend-out.log',
    },
  ],
}
