# KAIRO Final Runtime Hotfix

## Symptom
After successful authentication, the browser could show a blank page. In some environments the application could also feel unusually slow.

## Root cause fixed
The frontend trust rail contained a JavaScript reference typo (`fabricbric`) when rendering the authenticated application shell. That exception occurred immediately after login, so React could render a blank page even though authentication had succeeded.

## Performance hardening included
- Removed React StrictMode from the production-facing entrypoint to avoid duplicate development-side effects during demo use.
- Reduced system-status polling from every 5 seconds to every 10 seconds.
- Limited trust-rail health/blockchain requests to 4 seconds.
- Limited login to 10 seconds and session validation to 8 seconds.
- Limited dashboard/case loads to 10 seconds.
- Added short S3/MinIO connection/read timeouts and disabled SDK retry amplification for health checks.

## Demo rule
If the authenticated shell still does not appear, do not wait five minutes. The UI should surface a clear timeout/error. Check the backend at `http://127.0.0.1:8000/api/health` and then reload the frontend.
