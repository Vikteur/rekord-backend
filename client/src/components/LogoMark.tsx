/** The gradient brand mark — four white "equalizer" bars. Shared by the
 * sidebar and the sign-in screen so the app has one face everywhere. */
export function LogoMark() {
  return (
    <div className="logo-mark" aria-hidden>
      <span style={{ height: 7 }} />
      <span style={{ height: 12 }} />
      <span style={{ height: 5 }} />
      <span style={{ height: 9, opacity: 0.72 }} />
    </div>
  );
}
