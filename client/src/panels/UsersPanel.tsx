/** Admin-only: hand out and manage DJ logins.
 *
 * Every DJ gets exactly one account, made here (there is no sign-up). The
 * admin row is shown for completeness but can't be disabled or deleted —
 * the server refuses, so the buttons aren't offered.
 */
import { useEffect, useState } from 'react';
import { ApiError, api } from '../api';
import type { UserAccount } from '../types';
import { Panel } from './Panel';

const message = (error: unknown) =>
  error instanceof ApiError ? error.message : String(error);

export function UsersPanel() {
  const [users, setUsers] = useState<UserAccount[]>([]);
  const [error, setError] = useState('');
  const [username, setUsername] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState<string | null>(null); // which action runs
  const [resetFor, setResetFor] = useState<number | null>(null);
  const [newPassword, setNewPassword] = useState('');

  useEffect(() => {
    api
      .users()
      .then((data) => setUsers(data.users))
      .catch((err: unknown) => setError(message(err)));
  }, []);

  async function run(label: string, action: () => Promise<{ users: UserAccount[] }>) {
    setBusy(label);
    setError('');
    try {
      setUsers((await action()).users);
      return true;
    } catch (err) {
      setError(message(err));
      return false;
    } finally {
      setBusy(null);
    }
  }

  async function create() {
    const created = await run('create', () =>
      api.createUser(username.trim(), displayName.trim(), password),
    );
    if (created) {
      setUsername('');
      setDisplayName('');
      setPassword('');
    }
  }

  async function resetPassword(target: UserAccount) {
    const done = await run(`reset-${target.id}`, () =>
      api.updateUser(target.id, { password: newPassword }),
    );
    if (done) {
      setResetFor(null);
      setNewPassword('');
    }
  }

  async function remove(target: UserAccount) {
    const sure = window.confirm(
      `Delete the account ${target.username}?\n\nTheir couples and libraries stay, ` +
        'unowned — you can hand them to another DJ afterwards.',
    );
    if (!sure) return;
    await run(`delete-${target.id}`, () => api.deleteUser(target.id));
  }

  return (
    <Panel
      title="DJ accounts"
      subtitle="One login per DJ — each sees only their own couples and library."
    >
      <section className="panel-section">
        <h3 className="panel-section-title">New DJ</h3>
        <div className="stack">
          <input
            className="input"
            placeholder="e.g. sarah — their sign-in name"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
          />
          <input
            className="input"
            placeholder="e.g. Sarah V. — shown in the app"
            value={displayName}
            onChange={(event) => setDisplayName(event.target.value)}
          />
          <input
            className="input"
            type="password"
            placeholder="e.g. a starter password (min 8 characters)"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </div>
        <div className="field-row">
          <button
            className="btn btn-primary"
            title="Create the account and hand these details to the DJ"
            disabled={!username.trim() || password.length < 8 || busy !== null}
            onClick={create}
          >
            {busy === 'create' ? 'Creating…' : 'Create DJ account'}
          </button>
        </div>
      </section>

      <section className="panel-section">
        <h3 className="panel-section-title">Accounts</h3>
        <div className="list">
          {users.map((account) => (
            <div key={account.id} className="list-block">
              <div className="list-row">
                <span className="list-main">
                  <strong>{account.display_name}</strong>
                  <span className="muted"> · {account.username}</span>
                  {account.role === 'admin' && <span className="muted"> · admin</span>}
                  {account.disabled && <span className="warn"> · disabled</span>}
                </span>
                {account.role !== 'admin' && (
                  <span className="field-row">
                    <button
                      className="btn btn-ghost btn-sm"
                      title="Set a new password for this DJ"
                      onClick={() => {
                        setResetFor(resetFor === account.id ? null : account.id);
                        setNewPassword('');
                      }}
                    >
                      Reset password
                    </button>
                    <button
                      className="btn btn-ghost btn-sm"
                      title={
                        account.disabled
                          ? 'Let this DJ sign in again'
                          : 'Block sign-in and end their session'
                      }
                      onClick={() =>
                        void run(`disable-${account.id}`, () =>
                          api.updateUser(account.id, { disabled: !account.disabled }),
                        )
                      }
                    >
                      {account.disabled ? 'Enable' : 'Disable'}
                    </button>
                    <button
                      className="btn btn-ghost btn-sm"
                      title="Remove the account (their couples and libraries stay)"
                      onClick={() => void remove(account)}
                    >
                      Delete
                    </button>
                  </span>
                )}
              </div>
              {resetFor === account.id && (
                <div className="field-row list-detail">
                  <input
                    className="input"
                    style={{ flex: 1 }}
                    type="password"
                    placeholder="e.g. a fresh password (min 8 characters)"
                    value={newPassword}
                    onChange={(event) => setNewPassword(event.target.value)}
                  />
                  <button
                    className="btn btn-sm"
                    disabled={newPassword.length < 8 || busy !== null}
                    onClick={() => void resetPassword(account)}
                  >
                    {busy === `reset-${account.id}` ? 'Saving…' : 'Save password'}
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      </section>
      {error && <p className="error">{error}</p>}
    </Panel>
  );
}
