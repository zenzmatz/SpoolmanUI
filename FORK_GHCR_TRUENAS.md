# Fork GHCR Deployment For TrueNAS

This repository now includes a fork-specific GitHub Actions workflow for publishing a test image to GitHub Container Registry.

Workflow file:

- `.github/workflows/publish-fork-ghcr.yml`

## What it publishes

The workflow pushes a container image to:

- `ghcr.io/<your-github-user>/<your-repo-name>:latest`

It also pushes a commit-specific tag:

- `ghcr.io/<your-github-user>/<your-repo-name>:sha-<commit>`

If you manually trigger the workflow, you can also provide a custom image tag.

## Why this exists

The upstream CI workflow is designed for the upstream project and uses `donkie/spoolman` as the registry target.
That is not suitable for a personal fork you want to deploy from TrueNAS.

This workflow is additive and keeps the fork easy to rebase.

## GitHub setup

1. Push your modified Spoolman fork to GitHub.
2. Open the repository on GitHub.
3. Go to `Settings -> Actions -> General` and ensure GitHub Actions is enabled.
4. Go to `Settings -> Actions -> Workflow permissions` and allow:
   - read and write permissions
5. Save the setting.

The workflow uses `GITHUB_TOKEN`, so no manual GHCR secret is required for publishing to your own fork's package namespace.

## How to publish

### Option 1: Manual trigger

1. Open `Actions` in your fork.
2. Open `Publish Fork Image`.
3. Click `Run workflow`.
4. Optionally set `image_tag`.

### Option 2: Push-based trigger

Push to `main` or `master` and the workflow will publish automatically.

## TrueNAS image reference

In your TrueNAS app or compose config, use:

- `ghcr.io/<your-github-user>/<your-repo-name>:latest`

If you want an immutable deployment target, use a specific `sha-...` tag instead.

For your current fork, that resolves to:

- `ghcr.io/zenzmatz/spoolmaninsights:latest`

## TrueNAS config guidance

Keep your existing:

- environment variables
- database settings
- volume mounts
- port mappings

Only change the image reference to your GHCR image.

## First test checklist

After redeploying in TrueNAS:

1. Confirm the container starts successfully.
2. Open `/api/v1/info` and verify the app responds.
3. Open `/api/v1/insights/overview` and verify JSON is returned.
4. Open `/insights` and verify the dashboard loads.
5. Test material and location drill-down navigation.

## Current workflow limits

This fork workflow currently builds only `linux/amd64` to keep testing simple and fast.

If your TrueNAS system needs `arm64`, update the workflow `platforms:` entry to include it.