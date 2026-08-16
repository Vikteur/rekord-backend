import { useUi } from '../ui/UiContext';
import { AddPlaylistPanel } from './AddPlaylistPanel';
import { CouplesPanel } from './CouplesPanel';
import { ExportPanel } from './ExportPanel';
import { RememberedPanel } from './RememberedPanel';
import { SourcesScanPanel } from './SourcesScanPanel';
import { UsersPanel } from './UsersPanel';

/** Renders whichever secondary-flow panel is currently open. */
export function PanelHost() {
  const { activePanel } = useUi();
  switch (activePanel) {
    case 'sources':
      return <SourcesScanPanel />;
    case 'addPlaylist':
      return <AddPlaylistPanel />;
    case 'export':
      return <ExportPanel />;
    case 'remembered':
      return <RememberedPanel />;
    case 'couples':
      return <CouplesPanel />;
    case 'users':
      return <UsersPanel />;
    default:
      return null;
  }
}
