# Web Deployment Runbook

This runbook records the production location and automated deployment procedure
for the Deep Dig marketing site.

## Production target

| Item | Value |
| --- | --- |
| Public URL | `https://aiready.chat` |
| SSH host | `43.157.28.148` |
| Deployment user | `deepdig-deploy` (no root or sudo access) |
| Nginx config | `/etc/nginx/conf.d/aiready.conf` |
| Nginx document root | `/var/www/deep-dig-web/current` |
| Immutable releases | `/var/www/deep-dig-web/releases/<commit>-<attempt>` |
| Local source | `apps/web` |
| Local build output | `apps/web/dist` |

The dedicated deployment key is stored locally at
`~/.ssh/deep_dig_github_actions` and in the GitHub Actions secret
`DEPLOY_SSH_KEY`. Its public-key fingerprint is
`SHA256:B91jhM+TCOsp6R8DNd5mxu3r073XwzwVYKfjeZvHdag`. Never copy the private key
into this repository.

Nginx proxies `/mat-api/` to `http://127.0.0.1:8000/`; static deployments do not
change that proxy. The separate `compress.aiready.chat` site uses
`/var/www/docupix-pro` and is outside this deployment's scope.

## Automated CI/CD

The workflow at `.github/workflows/web-ci-cd.yml` performs two modes:

- Pull requests into `main`: install dependencies and run `pnpm build:web`.
- Pushes to `main` or manual runs: build, upload an immutable release, atomically
  switch the `current` symlink, and verify the public HTTPS page.

The workflow requires these repository Actions secrets:

| Secret | Purpose |
| --- | --- |
| `DEPLOY_HOST` | SSH hostname or IP address |
| `DEPLOY_USER` | Restricted deployment username |
| `DEPLOY_SSH_KEY` | Dedicated Ed25519 private key |
| `DEPLOY_KNOWN_HOSTS` | Pinned SSH host keys |

Ordinary releases should be made through a pull request into `main`. A release
can also be repeated from **GitHub → Actions → Web CI/CD → Run workflow**.

## Verify server state

```bash
ssh 43.157.28.148
readlink -f /var/www/deep-dig-web/current
nginx -t
curl -I https://aiready.chat/
```

The active path should resolve to a directory below
`/var/www/deep-dig-web/releases` and the homepage should return `200 OK`.

## Roll back

List releases, select a known-good directory, and atomically repoint `current`:

```bash
ssh 43.157.28.148
cd /var/www/deep-dig-web
ls -dt releases/*
ln -s releases/KNOWN_GOOD_RELEASE current.next
mv -Tf current.next current
curl -I https://aiready.chat/
```

The first version in the release layout is `releases/bootstrap`. The previous
pre-CI/CD Nginx configuration is backed up at
`/etc/nginx/conf.d/aiready.conf.pre-cicd-20260719-223112`, and the earlier static
site backup remains at
`/var/www/matextract-ai/dist.backup-20260719-220904`.
