import matplotlib.pyplot as plt
import matplotlib.patches as patches

def plot_bubble_mass_origins():
    fig, ax = plt.subplots(figsize=(12, 8), facecolor='white')
    ax.axis('off')
    ax.set_xlim(-1, 11)
    ax.set_ylim(-5, 5)

    # 1. Ambient ISM (Background)
    ism = patches.Rectangle((-1, -5), 12, 10, facecolor='#e0f2f1', edgecolor='none')
    ax.add_patch(ism)
    plt.text(9, 4, "Ambient ISM / Molecular Cloud\n(Unshocked)", 
             ha='center', va='center', fontsize=12, fontweight='bold', color='#00695c')

    # 2. Swept-Up Wall (The Snowplow Shell)
    wall = patches.Wedge((0, 0), 8, -60, 60, width=1.5, facecolor='#26a69a', edgecolor='black', lw=2)
    ax.add_patch(wall)
    
    # 3. Shocked Wind (Hot Bubble)
    hot_bubble = patches.Wedge((0, 0), 6.5, -60, 60, width=3.5, facecolor='#ffcc80', edgecolor='black', lw=2)
    ax.add_patch(hot_bubble)

    # 4. Free Wind Region
    free_wind = patches.Wedge((0, 0), 3, -60, 60, facecolor='#ffe0b2', edgecolor='black', lw=2)
    ax.add_patch(free_wind)

    # 5. Progenitor Star
    star = patches.Circle((0, 0), 0.3, facecolor='#d84315', edgecolor='black', zorder=10)
    ax.add_patch(star)
    plt.text(-0.5, 0, "Wolf-Rayet\nStar", ha='right', va='center', fontsize=12, fontweight='bold')

    # --- ARROWS AND ANNOTATIONS ---
    
    # Mass Source 1: The Star
    ax.annotate("", xy=(2.5, 0), xytext=(0.4, 0),
                arrowprops=dict(arrowstyle="->", lw=3, color='#d84315'))
    plt.text(1.5, 0.3, r"Mass Loss ($\dot{M}$)", ha='center', fontsize=11, color='#d84315', fontweight='bold')
    plt.text(1.5, -1, "FREE WIND\nMass strictly from star\n($\rho \propto r^{-2}$)", ha='center', va='top', fontsize=10)

    # Mass Source 2: Evaporation from the Wall
    ax.annotate("", xy=(5, 2), xytext=(6.4, 2),
                arrowprops=dict(arrowstyle="->", lw=3, color='#1565c0'))
    plt.text(5.5, 2.3, "Evaporation", ha='center', fontsize=11, color='#1565c0', fontweight='bold')
    plt.text(4.7, -2.5, "SHOCKED WIND\n(Hot Bubble)\nMass = Stellar Wind +\nEvaporated ISM", 
             ha='center', va='top', fontsize=10)

    # Mass Source 3: Swept up ISM
    ax.annotate("", xy=(7.5, 0), xytext=(9.5, 0),
                arrowprops=dict(arrowstyle="->", lw=4, color='#004d40'))
    plt.text(8.5, 0.3, "Bulldozed Mass", ha='center', fontsize=11, color='#004d40', fontweight='bold')
    
    plt.text(7.25, 3, "SWEPT-UP WALL\nMass = 100% Ambient ISM", 
             ha='center', va='center', fontsize=11, fontweight='bold', color='black',
             bbox=dict(facecolor='white', edgecolor='black', boxstyle='round,pad=0.5'))

    # Boundaries
    plt.text(3, -4.5, "Termination Shock", ha='center', fontsize=10, rotation=60)
    plt.text(6.5, -4.5, "Contact Discontinuity", ha='center', fontsize=10, rotation=60)
    plt.text(8, -4.5, "Forward Shock", ha='center', fontsize=10, rotation=60)

    plt.title("Mass Origins in a Wind-Blown Bubble Architecture", fontsize=16, fontweight='bold', pad=20)
    plt.tight_layout()
    plt.show()

plot_bubble_mass_origins()