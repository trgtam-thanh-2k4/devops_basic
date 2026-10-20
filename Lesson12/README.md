# Lesson 12: Nuxt static site on S3 + CloudFront

**Requirement:** Build a Nuxt project, deploy it with S3 + CloudFront, and submit the CloudFront link.

## Architecture

```
 Browser ── HTTPS ──▶ CloudFront distribution (d123abc.cloudfront.net)
                        │  viewer request → CloudFront Function "nuxt-index-rewrite"
                        │      /about  →  /about/index.html
                        │  Origin Access Control (OAC, SigV4 signed)
                        ▼
                      S3 bucket  lesson12-nuxt-<your-name>   (Block ALL public access = ON)
                        index.html, about/index.html, 200.html, 404.html, _nuxt/*.js|css

 Developer Mac ── npm run generate ──▶ .output/public ── upload ──▶ S3
```

Why this setup:
- The bucket stays **private**. Only CloudFront can read it, through OAC and the bucket policy. Users can't open S3 URLs directly.
- `nuxt generate` pre-renders each route as `<route>/index.html`. CloudFront's *Default root object* only works for `/`, so a small **CloudFront Function** rewrites `/about` to `/about/index.html`.

## Project files

| File | Purpose |
|---|---|
| `app/nuxt.config.ts` | Nuxt config |
| `app/app/app.vue` | Layout with nav and footer (shows build time) |
| `app/app/pages/index.vue` | Home page with a counter (checks that client-side JS works) |
| `app/app/pages/about.vue` | Second route (checks the CloudFront rewrite) |
| `app/.npmrc` | `legacy-peer-deps=true` (works around an npm 10 install bug) |
| `cloudfront/index-rewrite.js` | CloudFront Function code |
| `cloudfront/bucket-policy.json` | Bucket policy template (CloudFront usually generates it for you) |

---

## Step 1: Run locally

```bash
cd Lesson12/app
npm install
npm run dev            # http://localhost:3000, check Home + About + counter
```

📸 Evidence: `evidence/01-local-dev.png`

## Step 2: Build the static site

```bash
npm run generate
ls -R .output/public | head -30
npx serve .output/public   # optional: preview the static build at http://localhost:3000
```

You should see `index.html`, `about/index.html`, `200.html`, `404.html`, and `_nuxt/`.
**Upload what is inside `.output/public` (its contents), not the folder itself.**

📸 Evidence: `evidence/02-generate.png`

## Step 3: Create the S3 bucket

AWS Console → **S3** → **Create bucket**
- Region: `ap-southeast-1` (same as earlier lessons)
- Bucket type: General purpose
- Bucket name: `lesson12-nuxt-<your-name>` (must be globally unique)
- Object Ownership: ACLs disabled
- **Block all public access: ✅ ON** (keep the default)
- Versioning: Disable · Encryption: SSE-S3 (default)
- → **Create bucket**

Do **not** turn on "Static website hosting". With OAC, CloudFront reads from the S3 REST endpoint.

📸 Evidence: `evidence/03-s3-bucket.png`

## Step 4: Upload the build

Open the bucket → **Upload**
- Open Finder at `Lesson12/app/.output/public`, select **everything inside it** (`index.html`, `200.html`, `404.html`, `about/`, `_nuxt/`, `favicon.ico`…), and drag it in.
  Tip: `.output` is a hidden folder. In Finder press `Cmd+Shift+G` and paste the full path, or press `Cmd+Shift+.` to show hidden files.
- → **Upload**

Check: the bucket root should contain `index.html` and `_nuxt/`, **not** `public/` or `.output/`.

📸 Evidence: `evidence/04-s3-objects.png`

## Step 5: Create the CloudFront Function (URL rewrite)

CloudFront → **Functions** → **Create function**
- Name: `nuxt-index-rewrite` · Runtime: `cloudfront-js-2.0`
- Paste the code from `cloudfront/index-rewrite.js` → **Save changes**
- Tab **Publish** → **Publish function**

## Step 6: Create the CloudFront distribution

CloudFront → **Distributions** → **Create distribution**. The console uses a 4-step wizard. OAC is now a single checkbox. The function and the default root object are not in the wizard, so you set them after creation (6b).

### 6a. Wizard

1. **Get started**: distribution name `lesson12-nuxt`. Pick the **Free** plan if offered, otherwise pay-as-you-go.
2. **Specify origin**
   - Origin type: **Amazon S3**
   - S3 origin: **Browse S3** → choose `lesson12-nuxt-<your-name>`
   - Origin path: leave empty
   - ✅ **Allow private S3 bucket access to CloudFront - Recommended**. This creates the **OAC** for you and adds the bucket policy automatically.
   - Origin settings: **Use recommended origin settings**
   - Cache settings: **Use recommended cache settings tailored to serving S3 content** (`CachingOptimized`, HTTP redirected to HTTPS)
3. **Enable security**: **Do not enable** WAF (avoids extra cost)
4. **Review and create** → **Create distribution**

### 6b. Settings the wizard skips

- **Default root object**: distribution → **General** → **Settings** → **Edit** → Default root object `index.html` → **Save changes**
- **Function**: distribution → **Behaviors** → select `Default (*)` → **Edit** → bottom section **Function associations** → **Viewer request**: Function type `CloudFront Functions`, Function `nuxt-index-rewrite` → **Save changes**
  (Skip this if you use the custom error page method in Step 7.)

### 6c. Check OAC and bucket policy

- Distribution → **Origins** → select the origin → **Edit**: Origin access should show **Origin access control settings** with an OAC selected.
- S3 → bucket → **Permissions** → **Bucket policy**: it should allow `cloudfront.amazonaws.com` with your distribution ARN, like `cloudfront/bucket-policy.json`.
  If the policy is empty, the origin **Edit** page shows a **Copy policy** button. Paste the copied policy here and save.

📸 Evidence: `evidence/05-cloudfront-distribution.png`, `evidence/06-bucket-policy.png`

## Step 7: Custom 404 (optional, recommended)

Distribution → **Error pages** → **Create custom error response**
- HTTP error code: `403` (private S3 returns 403 for missing keys) → Customize: Yes → Response page path `/404.html` → HTTP response code `404`
- Repeat for error code `404`

## Step 8: Verify

Wait until **Last modified** changes from *Deploying* to a date (about 3–5 min). Then copy the **Distribution domain name**.

```bash
CF=https://dxxxxxxxxxxxx.cloudfront.net
curl -I $CF/                # 200, x-cache: Miss/Hit from cloudfront
curl -I $CF/about           # 200 (thanks to the CloudFront Function)
curl -I $CF/nope            # 404 (custom error page)
curl -I https://lesson12-nuxt-<your-name>.s3.ap-southeast-1.amazonaws.com/index.html   # 403 → bucket is private ✅
```

Open `$CF` in the browser, click Home/About, and press the counter button.

📸 Evidence: `evidence/07-browser-home.png`, `evidence/08-browser-about.png`, `evidence/09-curl.png`

## Step 9: Redeploy after changing code

```bash
npm run generate
```
Upload `.output/public/*` to S3 again (overwrite). Then CloudFront → distribution → **Invalidations** → **Create invalidation** → `/*`.
The footer build time should update.

## Step 10: Clean up (after the grade)

1. CloudFront → distribution → **Disable** → wait → **Delete**
2. CloudFront Functions → delete `nuxt-index-rewrite`; Origin access → delete OAC
3. S3 → bucket → **Empty** → **Delete**

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `AccessDenied` XML on `/` | Default root object not set to `index.html`, or bucket policy missing/wrong distribution ARN |
| `AccessDenied` on `/about` | CloudFront Function not published or not associated with *Viewer request* |
| Page loads but has no styles/JS | Files were uploaded inside a `public/` prefix. `_nuxt/` must be at the bucket root |
| Old content after redeploy | Create invalidation `/*` |
| `npm install` → `Cannot read properties of null (reading 'edgesOut')` | npm 10 bug. `.npmrc` already sets `legacy-peer-deps=true` |
