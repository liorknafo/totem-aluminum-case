"""Do the two parts still fit after machining? The top's underside and the bottom's top surface
as a Ø2 mm flat end mill leaves them (grey-level closing of each height map by a 1 mm disc, from
the side each is cut), and the smallest vertical gap between them."""
import sys
sys.path.insert(0, '.')
from geo import *
import mill, machinable
from scipy import ndimage

STEP = 0.05
for side in sys.argv[1:] or ['L', 'R']:
    top = machinable.surface_mesh(load(f'../outputs/TOTEM_alu_top_{side}.step'))
    bot = machinable.surface_mesh(load(f'../outputs/TOTEM_alu_bottom_{side}.step'))
    b = bot.bounds
    xs = np.arange(b[0, 0] - 2, b[1, 0] + 2, STEP) + 1.234e-4
    ys = np.arange(b[0, 1] - 2, b[1, 1] + 2, STEP) + 2.345e-4
    bt = machinable.projected_columns(bot, xs, ys)[0]
    tb = machinable.projected_columns(top, xs, ys)[1]
    ok = ~np.isnan(bt) & ~np.isnan(tb)
    fp = machinable.disc(1.0 - 0.03)
    lo, hi = np.nanmin(bt) - 10, np.nanmax(tb) + 10
    bm = ndimage.minimum_filter(ndimage.maximum_filter(np.where(np.isnan(bt), lo, bt), footprint=fp, mode='nearest'),
                                footprint=fp, mode='nearest')
    tm = ndimage.maximum_filter(ndimage.minimum_filter(np.where(np.isnan(tb), hi, tb), footprint=fp, mode='nearest'),
                                footprint=fp, mode='nearest')
    machined_overlap = (bm > lo + 1e-6) & (tm < hi - 1e-6)
    g_model = np.where(ok, tb - bt, np.nan)
    g_mach = np.where(machined_overlap, tm - bm, np.nan)
    print(f'{side}: smallest vertical gap top/bottom: as modelled {np.nanmin(g_model):.2f} mm, '
          f'both parts as a Ø2 mm end mill leaves them {np.nanmin(g_mach):.2f} mm', flush=True)
