# Internal deployment (GitHub + container)

This app is **Next.js** plus **Python** (`pcs_verify` and `scripts/`). Deploy it as a **Docker** image: GitHub Actions builds and pushes to **GitHub Container Registry (ghcr.io)**; your company hosts the image behind your **internal URL**.

## What was added in the repo

| File | Purpose |
|------|---------|
| `Dockerfile` | Production image: Node.js + Python venv + Next standalone server |
| `.dockerignore` | Smaller, faster builds |
| `.github/workflows/publish-ghcr.yml` | On push to `main`/`master`, builds and pushes the image to GHCR |
| `next.config.ts` | `output: "standalone"` so the image can run `node server.js` |

## 1. Push these changes to GitHub

Commit and push the new files to the branch GitHub uses as default (usually `main`). That triggers the workflow.

## 2. Confirm the workflow succeeded

On GitHub: **Actions** → **Publish container to GHCR** → latest run should be green.

The image name is:

`ghcr.io/<owner>/<repo>:latest`

(Your `<owner>` is your GitHub user or organization, `<repo>` is the repository name.)

## 3. Company hosting options (choose one)

- **Kubernetes / OpenShift** — deploy a Deployment that uses this image, Service, and Ingress (or Route) for the internal hostname.
- **Azure App Service / Container Apps, AWS ECS, etc.** — create an app from the container image and attach your internal domain / private endpoint per your IT standards.
- **A Linux VM** — install Docker, `docker pull` the image, `docker run` (see below), put **HTTPS + internal DNS** in front (reverse proxy or load balancer).

## 4. Run the app (Docker Compose — recommended)

From a machine with Docker installed, clone the repo **or** copy `docker-compose.yml` and point the `image` at your GHCR package.

**Build and run from source (no pull needed):**

```bash
docker compose up --build -d
```

**Run the image GitHub Actions published** (log in to `ghcr.io` first if the package is private):

```bash
docker compose pull
docker compose up -d
```

Open **http://localhost:3000** (or your server’s hostname on port 3000). For an internal URL, put a reverse proxy / ingress in front that serves HTTPS and your company DNS name.

## 4b. Run the container (docker run)

Replace the image with yours from step 2.

```bash
docker pull ghcr.io/OWNER/REPO:latest
docker run -d --name pcs-check -p 3000:3000 ghcr.io/OWNER/REPO:latest
```

Then open `http://<server>:3000` on the internal network, or configure your proxy to serve `https://pcs-check.yourcompany.internal` → port 3000.

**Port:** The app listens on `PORT` (default **3000** in the image).

## 5. GitHub Container Registry access (company / private)

If the pull fails with “unauthorized”:

1. In GitHub: **Package settings** for this image → set visibility to what your policy allows (**internal** for GitHub Enterprise Cloud orgs, or **private** with a PAT / `GITHUB_TOKEN` for CI elsewhere).
2. On the server or in your orchestrator, authenticate to `ghcr.io` with a user or service account that can read the package.

## 6. Smoke test after deploy

1. Open the app in a browser (internal URL).
2. Use **PDF → Word** or **Verify** with a sample from `public/samples/` (upload paths may be under **/samples/** in the UI).

If API routes fail with Python errors, confirm the container log shows no missing module errors (the image runs `pip install -r requirements.txt` at build time).

---

**Draft:** Have IT or your platform team review networking, authentication, and data handling before you point users at the internal URL.
