export function AnimatedBackground() {
    // Render a static, non-animated decorative background composed of
    // layered radial gradients. This keeps the aesthetic but avoids
    // the ongoing animation work and large repaint/composite cost.
    return (
        <div className="fixed inset-0 -z-10 overflow-hidden bg-slate-50 pointer-events-none static-blobs" />
    );
}
