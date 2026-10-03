#!/usr/bin/env python3
"""make_fig1_v2.py - mechanism figure tied to Algorithms 1-3."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Polygon, Circle, Rectangle

C_SRC_BG, C_NET_BG, C_RCV_BG = "#EEF3F8", "#EFF5EC", "#FBF3EC"
C_SRC_F, C_SRC_E = "#D7E4F2", "#2E5C8A"
C_RCV_F, C_RCV_E = "#F9E2D2", "#B5651D"
C_DIA_F, C_DIA_E = "#FCEFC7", "#BF9000"
C_CHUNK, C_PAR = "#56B4E9", "#009E73"
C_DROP = "#D55E00"
C_TXT = "#1a1a1a"

fig, ax = plt.subplots(figsize=(170 / 25.4, 110 / 25.4))
ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.axis("off")

def rbox(x, y, w, h, fc, ec, lw=1.1, rs=0.9, z=3):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={rs}",
                                fc=fc, ec=ec, lw=lw, zorder=z))

def txt(x, y, s, size=7.2, ha="center", va="center", color=C_TXT, z=7, weight="normal"):
    ax.text(x, y, s, fontsize=size, ha=ha, va=va, color=color, zorder=z, weight=weight)

def arrow(x1, y1, x2, y2, color="#444444", lw=1.3, z=5, ms=9):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=ms,
                                 lw=lw, color=color, zorder=z, shrinkA=1, shrinkB=1))

def diamond(cx, cy, w, h, fc, ec, z=4):
    pts = [(cx, cy + h / 2), (cx + w / 2, cy), (cx, cy - h / 2), (cx - w / 2, cy)]
    ax.add_patch(Polygon(pts, closed=True, fc=fc, ec=ec, lw=1.1, zorder=z))

def lane(y0, y1, fc, label, lc):
    ax.add_patch(Rectangle((1.5, y0), 97, y1 - y0, fc=fc, ec="none", zorder=1))
    ax.plot([1.5, 98.5], [y1, y1], color="#c9c9c9", lw=0.7, zorder=2)
    txt(2.6, y1 - 2.4, label, size=7.8, ha="left", color=lc, weight="bold")

# lanes
lane(76, 98, C_SRC_BG, "Source", "#2E5C8A")
lane(40, 64, C_NET_BG, "Multicast network", "#3f7d3f")
lane(4, 32, C_RCV_BG, "Receiver", "#B5651D")

# ---- source pipeline ----
sy = 84.0
rbox(13, sy - 5.5, 16, 11, C_SRC_F, C_SRC_E)
txt(21, sy + 1.6, "Buffer n packets", 6.9); txt(21, sy - 2.2, r"form block $B_i$", 6.9)
txt(13.7, sy + 4.6, "Alg. 1", 6.1, ha="left", color=C_SRC_E, weight="bold")
arrow(29.2, sy, 31.8, sy)
rbox(32, sy - 5.5, 14, 11, C_SRC_F, C_SRC_E)
txt(39, sy + 1.6, r"$h_{i-1}=$", 6.9); txt(39, sy - 1.4, r"$H(B_{i-1})$", 6.9)
arrow(46.2, sy, 48.8, sy)
rbox(49, sy - 5.5, 21, 11, C_SRC_F, C_SRC_E)
txt(59.5, sy + 1.8, r"$\sigma_i=\mathrm{Sign}_{sk}($", 6.9)
txt(59.5, sy - 1.3, r"$i\,\|\,B_i\,\|\,h_{i-1})$", 6.9)
arrow(70.2, sy, 72.8, sy)
rbox(73, sy - 5.5, 24, 11, C_SRC_F, C_SRC_E)
txt(85, sy + 1.8, "MTU-aware FEC", 7.0, weight="bold"); txt(85, sy - 2.2, "of signature record", 6.6)
txt(73.7, sy + 4.6, "Alg. 3", 6.1, ha="left", color=C_SRC_E, weight="bold")

# ---- signature record zoom ----
zy = 68.8
gstep, kw0, kh, kx = 5.7, 5.0, 5.0, 11
txt(kx, zy + 3.0, r"record $M_\sigma=s_\sigma+tH+\ell_{\rm kid}$", 6.7, ha="left")
for i in range(4):
    x0 = kx + i * gstep
    ax.add_patch(Rectangle((x0, zy - kh / 2), kw0, kh,
                           fc=C_CHUNK, ec="#1f6f96", lw=0.8, zorder=4))
    txt(x0 + kw0 / 2, zy, f"c{i+1}", 5.7, color="white")
txt(kx + 2 * gstep - 1, zy - 4.5, r"$k_s=\lceil M_\sigma/C\rceil$ source chunks", 6.1)
px0 = kx + 4 * gstep + 1.0
txt(px0 + 1.0, zy, "+", 9)
for i in range(2):
    x0 = px0 + 2.8 + i * gstep
    ax.add_patch(Rectangle((x0, zy - kh / 2), kw0, kh,
                           fc=C_PAR, ec="#1f6b4d", lw=0.8, hatch="////", zorder=4))
    txt(x0 + kw0 / 2, zy, f"p{i+1}", 5.5, color="white")
txt(px0 + 2.8 + gstep - 1, zy - 4.5, r"$\lceil\rho k_s\rceil$ parity", 6.1)
arrow(px0 + 2.8 + 2 * gstep + 1.2, zy, 96.5, zy, color="#1f6b4d", lw=1.2)
txt(96.2, zy + 2.8, r"recover from any $k_s$ of $n_c$", 6.3, ha="right", color="#1f6b4d")

# ---- network multicast tree ----
def router(cx, cy, r=2.3):
    ax.add_patch(Circle((cx, cy), r, fc="#ffffff", ec="#555555", lw=1.0, zorder=5))
    ax.plot([cx - r * 0.6, cx + r * 0.6], [cy, cy], color="#555555", lw=0.8, zorder=6)
    ax.plot([cx, cx], [cy - r * 0.6, cy + r * 0.6], color="#555555", lw=0.8, zorder=6)

arrow(50, 76, 50, 60.8, color="#777777", lw=1.2)
txt(63, 62.4, "one multicast of every packet", 6.2, ha="left")
router(50, 58.2, 2.6)
router(27, 50); router(73, 50)
arrow(48.2, 56.8, 28.6, 52.0, color="#777777", lw=1.1)
arrow(51.8, 56.8, 71.4, 52.0, color="#777777", lw=1.1)
leaf_x = [12, 33, 67, 88]
for lx, px in zip(leaf_x, [27, 27, 73, 73]):
    arrow(px, 48.0, lx, 43.4, color="#777777", lw=1.0)
    ax.add_patch(Circle((lx, 42), 1.5, fc="#ffffff", ec="#555555", lw=0.9, zorder=5))
    for j, t in enumerate([0.2, 0.5, 0.8]):
        mx = px + t * (lx - px); my = 48.0 + t * (43.4 - 48.0)
        drop = (int(lx) in (12, 67)) and j == 1
        if drop:
            ax.add_patch(Rectangle((mx - 1.1, my - 1.1), 2.2, 2.2, fc=C_DROP, ec="none", zorder=7))
            ax.plot([mx - 0.8, mx + 0.8], [my - 0.8, my + 0.8], color="white", lw=1.0, zorder=8)
            ax.plot([mx - 0.8, mx + 0.8], [my + 0.8, my - 0.8], color="white", lw=1.0, zorder=8)
        else:
            col = C_PAR if j == 2 else C_CHUNK
            ax.add_patch(Rectangle((mx - 0.9, my - 0.9), 1.8, 1.8, fc=col, ec="none", zorder=6))
txt(97.8, 55.3, "per-receiver last-mile loss $p$", 6.3, ha="right", color="#8a3a1a")

# ---- receiver pipeline ----
ry = 16.5
rbox(11, ry - 5.0, 11, 10, "#ffffff", "#999999", lw=0.9)
txt(16.5, ry + 1.6, "reorder", 6.5); txt(16.5, ry - 2.0, "buffer", 6.5)
arrow(22.2, ry, 24.4, ry)
diamond(27.5, ry, 9, 12, C_DIA_F, C_DIA_E)
txt(27.5, ry + 1.8, r"$D_i$:", 6.6, weight="bold"); txt(27.5, ry - 2.0, "n packets?", 6.2)
arrow(32.2, ry, 34.4, ry)
diamond(38, ry, 9, 12, C_DIA_F, C_DIA_E)
txt(38, ry + 1.8, r"$S_i$:", 6.6, weight="bold"); txt(38, ry - 2.0, r"$\geq k_s$ chunks?", 5.8)
arrow(42.7, ry, 44.9, ry)
rbox(45, ry - 5.0, 12, 10, C_RCV_F, C_RCV_E)
txt(51, ry + 1.6, "replay window", 6.3); txt(51, ry - 2.0, r"$W$ (bitmap)", 6.3)
arrow(57.2, ry, 59.4, ry)
rbox(59.5, ry - 5.0, 19, 10, C_RCV_F, C_RCV_E)
txt(69, ry + 1.7, r"check $h_{i-1}$,", 6.4); txt(69, ry - 1.9, r"$\mathrm{Verify}_{pk}(\sigma_i)$", 6.3)
txt(60.2, ry + 4.2, "Alg. 2", 5.9, ha="left", color=C_RCV_E, weight="bold")
arrow(78.7, ry, 80.9, ry)
rbox(81, ry - 5.0, 12.5, 10, "#D8EEDF", "#2a7d46")
txt(87.25, ry, "Accept $B_i$", 6.7, color="#1d5a31", weight="bold")
for dx in (27.5, 38):
    arrow(dx, ry - 6.2, dx, 8.6, color="#999999", lw=1.0)
txt(33, 6.9, "defer (keep bounded state, do not accept)", 6.2, color="#666666")
arrow(12, 40.3, 16.0, 21.6, color="#888888", lw=1.0)

plt.savefig("/mnt/e/pqc+zhengshu/pq-net-research/paper/figs/fig1_mechanism_v2.pdf",
            bbox_inches="tight", pad_inches=0.02)
plt.savefig("/mnt/e/pqc+zhengshu/pq-net-research/paper/figs/fig1_mechanism_v2.png",
            dpi=300, bbox_inches="tight", pad_inches=0.02)
print("fig1 done")
