"""
Google Antigravity Cursor-Following Background Canvas Animation for MARIP.
Recreates the interactive particle/dot grid and cursor glow effect from https://antigravity.google/.
Self-contained module; injected via streamlit.components.v1.html.
"""

import streamlit as st
import streamlit.components.v1 as components

CURSOR_BG_SCRIPT = """
<script>
(function() {
    try {
        const parentDoc = window.parent.document;
        const parentWin = window.parent;

        if (!parentDoc || !parentWin) return;

        // Cleanup existing instances to prevent duplicate loops on Streamlit reruns
        if (parentWin.__ag_bg_cleanup) {
            parentWin.__ag_bg_cleanup();
        }

        let canvas = parentDoc.getElementById("ag-cursor-canvas");
        if (!canvas) {
            canvas = parentDoc.createElement("canvas");
            canvas.id = "ag-cursor-canvas";
            canvas.style.position = "fixed";
            canvas.style.top = "0";
            canvas.style.left = "0";
            canvas.style.width = "100vw";
            canvas.style.height = "100vh";
            canvas.style.zIndex = "0";
            canvas.style.pointerEvents = "none";
            parentDoc.body.prepend(canvas);
        }

        const ctx = canvas.getContext("2d");
        if (!ctx) return;

        // Check prefers-reduced-motion
        const motionQuery = parentWin.matchMedia('(prefers-reduced-motion: reduce)');
        if (motionQuery.matches) {
            canvas.style.display = "none";
            return;
        }

        let width = 0;
        let height = 0;
        let dpr = parentWin.devicePixelRatio || 1;
        let points = [];
        const SPACING = 32; // Distance between grid dots
        const INFLUENCE_RADIUS = 190; // Cursor interaction zone
        const MAX_DISPLACEMENT = 28; // Max push distance

        // Smoothed cursor coordinates (lerp)
        const mouse = {
            x: -9999,
            y: -9999,
            targetX: -9999,
            targetY: -9999,
            active: false
        };

        function resize() {
            width = parentWin.innerWidth;
            height = parentWin.innerHeight;
            dpr = parentWin.devicePixelRatio || 1;

            canvas.width = width * dpr;
            canvas.height = height * dpr;
            ctx.scale(dpr, dpr);

            // Rebuild grid
            points = [];
            const cols = Math.ceil(width / SPACING) + 2;
            const rows = Math.ceil(height / SPACING) + 2;

            for (let i = 0; i < cols; i++) {
                for (let j = 0; j < rows; j++) {
                    const ox = i * SPACING;
                    const oy = j * SPACING;
                    points.push({
                        ox: ox,
                        oy: oy,
                        x: ox,
                        y: oy,
                        vx: 0,
                        vy: 0,
                        baseRadius: 1.15
                    });
                }
            }
        }

        resize();

        function onMouseMove(e) {
            mouse.targetX = e.clientX;
            mouse.targetY = e.clientY;
            mouse.active = true;
        }

        function onMouseLeave() {
            mouse.targetX = -9999;
            mouse.targetY = -9999;
            mouse.active = false;
        }

        parentWin.addEventListener("mousemove", onMouseMove, { passive: true });
        parentWin.addEventListener("mouseleave", onMouseLeave, { passive: true });
        parentWin.addEventListener("resize", resize, { passive: true });

        let animationFrameId = null;

        function animate() {
            if (parentDoc.hidden) {
                animationFrameId = requestAnimationFrame(animate);
                return;
            }

            // Smooth cursor trailing
            if (mouse.active) {
                mouse.x += (mouse.targetX - mouse.x) * 0.12;
                mouse.y += (mouse.targetY - mouse.y) * 0.12;
            } else {
                mouse.x = -9999;
                mouse.y = -9999;
            }

            ctx.clearRect(0, 0, width, height);

            // 1. Draw soft radial glow behind cursor
            if (mouse.active && mouse.x > -500) {
                const glow = ctx.createRadialGradient(
                    mouse.x, mouse.y, 0,
                    mouse.x, mouse.y, INFLUENCE_RADIUS * 1.1
                );
                glow.addColorStop(0, "rgba(66, 133, 244, 0.11)"); // Google Blue
                glow.addColorStop(0.4, "rgba(161, 66, 244, 0.05)"); // Antigravity Violet
                glow.addColorStop(0.7, "rgba(245, 56, 160, 0.02)"); // Pink
                glow.addColorStop(1, "rgba(255, 255, 255, 0)");

                ctx.fillStyle = glow;
                ctx.beginPath();
                ctx.arc(mouse.x, mouse.y, INFLUENCE_RADIUS * 1.1, 0, Math.PI * 2);
                ctx.fill();
            }

            // 2. Update and draw particles
            for (let i = 0; i < points.length; i++) {
                const p = points[i];

                let targetX = p.ox;
                let targetY = p.oy;
                let r = p.baseRadius;
                let color = "rgba(201, 211, 234, 0.55)"; // Default subtle gray-blue

                if (mouse.active) {
                    const dx = p.ox - mouse.x;
                    const dy = p.oy - mouse.y;
                    const dist = Math.hypot(dx, dy);

                    if (dist < INFLUENCE_RADIUS && dist > 0.001) {
                        const factor = Math.pow(1 - dist / INFLUENCE_RADIUS, 1.4);
                        const push = factor * MAX_DISPLACEMENT;
                        const angle = Math.atan2(dy, dx);

                        targetX = p.ox + Math.cos(angle) * push;
                        targetY = p.oy + Math.sin(angle) * push;

                        // Size expansion
                        r = p.baseRadius + factor * 1.6;

                        // Google Antigravity gradient transition
                        if (dist < INFLUENCE_RADIUS * 0.35) {
                            color = `rgba(245, 56, 160, ${0.45 + factor * 0.45})`; // Pink accent
                        } else if (dist < INFLUENCE_RADIUS * 0.65) {
                            color = `rgba(161, 66, 244, ${0.4 + factor * 0.4})`; // Violet accent
                        } else {
                            color = `rgba(66, 133, 244, ${0.35 + factor * 0.35})`; // Google Blue accent
                        }
                    }
                }

                // Spring back physics
                p.vx += (targetX - p.x) * 0.1;
                p.vy += (targetY - p.y) * 0.1;
                p.vx *= 0.78;
                p.vy *= 0.78;
                p.x += p.vx;
                p.y += p.vy;

                // Render dot
                ctx.fillStyle = color;
                ctx.beginPath();
                ctx.arc(p.x, p.y, r, 0, Math.PI * 2);
                ctx.fill();
            }

            animationFrameId = requestAnimationFrame(animate);
        }

        animationFrameId = requestAnimationFrame(animate);

        // Store cleanup hook
        parentWin.__ag_bg_cleanup = function() {
            if (animationFrameId) {
                cancelAnimationFrame(animationFrameId);
            }
            parentWin.removeEventListener("mousemove", onMouseMove);
            parentWin.removeEventListener("mouseleave", onMouseLeave);
            parentWin.removeEventListener("resize", resize);
        };
    } catch (err) {
        console.warn("Google Antigravity cursor canvas failed to initialize:", err);
    }
})();
</script>
"""

TRANSPARENT_CONTAINERS_CSS = """
<style>
/* ═══ Transparency for Antigravity Cursor Canvas Background ═════════════════ */
.stApp,
[data-testid="stApp"],
[data-testid="stAppViewContainer"],
[data-testid="stHeader"],
.main .block-container {
    background: transparent !important;
}

/* Semi-opaque backdrop for cards and sidebar so text stays 100% crisp */
[data-testid="stSidebar"] {
    background: rgba(248, 249, 252, 0.92) !important;
    backdrop-filter: blur(14px) !important;
    -webkit-backdrop-filter: blur(14px) !important;
}

.hero-header {
    background: rgba(255, 255, 255, 0.92) !important;
    backdrop-filter: blur(12px) !important;
    -webkit-backdrop-filter: blur(12px) !important;
}

.metric-card,
.agent-card,
.timeline-entry,
.report-container,
.fc-card,
[data-testid="stExpander"] {
    background: rgba(255, 255, 255, 0.90) !important;
    backdrop-filter: blur(10px) !important;
    -webkit-backdrop-filter: blur(10px) !important;
}
</style>
"""


def inject_cursor_background():
    """Inject the interactive cursor-following particle canvas and transparency styles."""
    # 1. Apply transparency overrides so canvas shines through
    st.markdown(TRANSPARENT_CONTAINERS_CSS, unsafe_allow_html=True)

    # 2. Inject canvas DOM element and script into window.parent
    components.html(CURSOR_BG_SCRIPT, height=0, width=0)

