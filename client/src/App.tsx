import { AppProvider } from './store';
import { UiProvider } from './ui/UiContext';
import { AppShell } from './components/AppShell';
import { AuthProvider, useAuth } from './auth';
import { LoginView } from './components/LoginView';

/** Mounting the store only when signed in means its startup fetches never
 * fire logged out — and remounting after sign-in refetches everything for
 * whoever just signed in. */
function Gate() {
  const { status } = useAuth();
  if (status === 'checking') return null; // one blank beat while /api/me answers
  if (status === 'anon') return <LoginView />;
  return (
    <AppProvider>
      <UiProvider>
        <AppShell />
      </UiProvider>
    </AppProvider>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <Gate />
    </AuthProvider>
  );
}
