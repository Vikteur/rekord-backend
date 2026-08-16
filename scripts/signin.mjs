// Shared sign-in for the smoke checks: the app has a real login now, so every
// script that drives the DJ UI or DJ API needs a session first.
//
// Scripts that spawn their own server pass SMOKE_CREDS as ADMIN_USERNAME /
// ADMIN_PASSWORD (first-boot bootstrap on a throwaway REKORD_DB). Scripts that
// attach to an already-running app need real credentials via
// SMOKE_USERNAME / SMOKE_PASSWORD.

export const SMOKE_CREDS = {
  username: process.env.SMOKE_USERNAME ?? 'smoke',
  password: process.env.SMOKE_PASSWORD ?? 'smoke-check-pass',
};

/** Sign in over HTTP; resolves to the raw rm_session cookie value. */
export async function signIn(baseUrl) {
  const response = await fetch(new URL('/api/auth/login', baseUrl), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(SMOKE_CREDS),
  });
  if (!response.ok) {
    throw new Error(
      `sign-in failed (${response.status}) for "${SMOKE_CREDS.username}" — ` +
        'set SMOKE_USERNAME / SMOKE_PASSWORD to an account that exists on the target app',
    );
  }
  const cookie = response.headers.get('set-cookie')?.match(/rm_session=([^;]+)/)?.[1];
  if (!cookie) throw new Error('login answered 200 but set no rm_session cookie');
  return cookie;
}

/** Sign in and plant the session cookie on a Playwright BrowserContext. */
export async function addSession(context, baseUrl) {
  const value = await signIn(baseUrl);
  await context.addCookies([{ name: 'rm_session', value, url: baseUrl }]);
  return value;
}
