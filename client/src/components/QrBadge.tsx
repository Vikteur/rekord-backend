/** A QR code for a magic link — printed, shown at the venue, or passed
 * around a table faster than any typed URL.
 *
 * Deliberately NOT theme-tokenized: scanners want dark modules on a white
 * field with a quiet zone around them, in booth mode too, so the card is
 * always white with black modules.
 */
import { QRCodeSVG } from 'qrcode.react';

export function QrBadge({ url, label }: { url: string; label?: string }) {
  return (
    <figure className="qr-card">
      <QRCodeSVG value={url} size={168} marginSize={2} bgColor="#ffffff" fgColor="#000000" />
      {label && <figcaption className="qr-caption">{label}</figcaption>}
    </figure>
  );
}
