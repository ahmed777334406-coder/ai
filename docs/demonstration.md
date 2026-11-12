# Professor demonstration

Use fictional accounts and item descriptions. Do not upload real student IDs or ownership evidence.

1. Register two student accounts, Owner and Finder, with private passwords.
2. As Owner, report a black backpack lost near University Library. Include a fictional identifying detail only in the private field.
3. As Finder, report a black school bag found by the library entrance; choose the same Bags category and library zone. Upload the sample backpack image if desired.
4. As Owner, open Matches. Review the score, component signals and the visible fallback/model label. Scores express similarity, never verified ownership or calibrated probability.
5. Open the found item from the match and submit a claim with the fictional identifying detail.
6. Sign in as the privately provisioned administrator. Open Claims, review evidence and approve or reject.
7. Check Claims and both item pages. Approval recovers both matched reports; rejection keeps available reports open. Check notifications for both students.
8. Switch between English and Chinese with the top language button. Inspect the mobile layout.

## Administrator setup

In the **SmartFind** Railway backend variables, set `ADMIN_EMAIL` to your administrator address and `ADMIN_PASSWORD` to a unique private password of at least 16 characters, then redeploy. Bootstrap creates an administrator only if that address does not exist. It refuses to promote an existing student automatically. Do not use local demo credentials on the public site.

## Live AI

Set `GEMINI_API_KEY` privately in Railway and `GEMINI_MODEL` to a model available to that key (default `gemini-2.5-flash`). No key belongs in Vercel public variables. Failed or unconfigured requests return labeled deterministic fallbacks. For E5/OpenCLIP, build with `INSTALL_AI_DEPS=true`, set `ENABLE_LOCAL_MODELS=true`, and provision enough memory and a model cache. Installing the SDK does not establish a successful API call or model-quality metric.
