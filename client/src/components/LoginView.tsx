/** The sign-in gate: what anyone without a session sees instead of the app.
 *
 * Accounts are handed out by the admin — there is deliberately no sign-up
 * link. Couples and their friends never see this screen; their magic link
 * (/g/<token>) is their login.
 */
import { useState, type FormEvent } from 'react';
import { ApiError } from '../api';
import { useAuth } from '../auth';
import { LogoMark } from './LogoMark';

export function LoginView() {
  const { signIn } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      await signIn(username.trim(), password);
    } catch (exc) {
      setError(exc instanceof ApiError ? exc.message : String(exc));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="login-view">
      <form className="login-card" onSubmit={submit}>
        <div className="brand login-brand">
          <LogoMark />
          <span className="brand-name">Rekord Match</span>
        </div>
        <p className="hint login-hint">
          Sign in with the account your admin set up. Couples and friends
          don’t sign in — their magic link is their key.
        </p>
        <label className="field-label" htmlFor="login-username">
          Username
        </label>
        <input
          id="login-username"
          className="input"
          placeholder="e.g. viktor"
          autoComplete="username"
          autoFocus
          value={username}
          onChange={(event) => setUsername(event.target.value)}
        />
        <label className="field-label" htmlFor="login-password">
          Password
        </label>
        <input
          id="login-password"
          className="input"
          type="password"
          placeholder="e.g. your DJ password"
          autoComplete="current-password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />
        {error && <p className="error">{error}</p>}
        <button
          className="btn btn-primary btn-block"
          type="submit"
          title="Open the DJ app with this account"
          disabled={busy || !username.trim() || !password}
        >
          {busy ? 'Signing in…' : 'Sign in'}
        </button>
      </form>
    </div>
  );
}
