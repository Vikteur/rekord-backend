/** Who is signed in, app-wide.
 *
 * On mount, one `GET /api/me` decides between the sign-in screen and the app.
 * Any later 401 from any API call fires the shared signed-out event (see
 * api.ts) and flips the app back to the sign-in screen — so an expired or
 * revoked session never leaves someone clicking dead buttons.
 */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import { api, SIGNED_OUT_EVENT } from './api';
import type { Me } from './types';

type AuthStatus = 'checking' | 'anon' | 'authed';

interface AuthValue {
  status: AuthStatus;
  user: Me | null;
  signIn: (username: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<Me | null>(null);
  const [status, setStatus] = useState<AuthStatus>('checking');

  useEffect(() => {
    api
      .me()
      .then((data) => {
        setUser(data.user);
        setStatus('authed');
      })
      .catch(() => setStatus('anon'));
  }, []);

  useEffect(() => {
    const onSignedOut = () => {
      setUser(null);
      setStatus('anon');
    };
    window.addEventListener(SIGNED_OUT_EVENT, onSignedOut);
    return () => window.removeEventListener(SIGNED_OUT_EVENT, onSignedOut);
  }, []);

  const signIn = useCallback(async (username: string, password: string) => {
    const data = await api.login(username, password);
    setUser(data.user);
    setStatus('authed');
  }, []);

  const signOut = useCallback(async () => {
    await api.logout().catch(() => undefined); // dead session = already out
    setUser(null);
    setStatus('anon');
  }, []);

  const value = useMemo(
    () => ({ status, user, signIn, signOut }),
    [status, user, signIn, signOut],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error('useAuth must be used inside AuthProvider');
  return value;
}
