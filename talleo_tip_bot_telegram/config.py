import yaml
from munch import Munch
import argparse
import sys

config = None


def load_config():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', nargs='?', help='configuration file',
                        default='../config.yml')
    args, left = parser.parse_known_args()
    sys.argv = sys.argv[:1] + left
    print("Loading configuration file {}".format(args.config))
    with open(args.config) as config_file:
        _config = yaml.load(config_file, Loader=yaml.Loader)
        globals()['config'] = Munch.fromDict(_config)


load_config()
