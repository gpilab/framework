
# Define paths
import os, sys

HERE = os.path.abspath(__file__)
THISDIR = os.path.dirname(HERE)
GPIREPO = os.path.realpath(os.path.join(THISDIR, '..', 'lib', 'gpi'))
ICONFILE = os.path.join(GPIREPO, 'graphics', 'gpi.icns')

sys.path.append(GPIREPO)

def make_disk_image(dist_dir, make_lite=False):
    """
    Make macOS disk image containing Spyder.app application bundle.
    Parameters
    ----------
    dist_dir : str
        Directory in which to put the disk image.
    make_lite : bool, optional
        Whether to append the disk image file and volume name with 'Lite'.
        The default is False.
    """
    print('Creating disk image...')

    from dmgbuild import build_dmg
    from dmgbuild.core import DMGError

    volume_name = '{}-{} Py-{}.{}.{}'.format("GPI", "1.0.0", "3", "7", "11")
    dmgfile = os.path.join(dist_dir, 'GPI')

    dmgfile += '.dmg'

    settings_file = os.path.join(THISDIR, 'dmg_settings.py')
    settings = {
        'files': [os.path.join(dist_dir, 'gpi_launch.app')],
        'badge_icon': ICONFILE,
        'icon_locations': {'gpi_launch.app': (140, 120),
                           'Applications': (500, 120)}
    }

    try:
        build_dmg(dmgfile, volume_name, settings_file=settings_file,
                  settings=settings, detach_retries=30)
        print('Building disk image complete.')
    except DMGError as exc:
        if exc.args[0] == 'Unable to detach device cleanly':
            # don't raise this error since the dmg is forced to detach
            print(exc.args[0])
        else:
            raise exc

    return

if __name__ == '__main__':
    make_disk_image(os.path.realpath(os.path.join(THISDIR, 'dist')))