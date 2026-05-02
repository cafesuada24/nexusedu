export function AnimatedBackground() {
    return (
        <div className="fixed inset-0 -z-10 overflow-hidden bg-slate-50 pointer-events-none">
            <div className="animated-bg-blob blob-1" />
            <div className="animated-bg-blob blob-2" />
            <div className="animated-bg-blob blob-3" />
        </div>
    );
}
