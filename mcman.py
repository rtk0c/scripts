import argparse
import mcsetup

if __name__ == '__main__':
	parser = argparser.ArgumentParser()
	parser.add_argument('-D', '--data-dir', default='', help='Data directory for storing downloaded files. Leave empty to use the platform default.')
	subparsers = parser.add_subparsers(dest='subparser_name', help='subcommands')

	subparser_store = subparsers.add_parser('store', help='Store a server instance as a template.')
    subparser_store.add_argument('dir')
    subparser_store.add_argument('--server-jar', default='server.jar', help='File name of the server jar. Useful to set this if e.g. a mod loader is used and its file name includes version numbers, etc.')
    subparser_store.add_argument('--global-share', nargs='+', default=['libraries'])
    subparser_store.add_argument('--instance-share', nargs='+', default=['versions', 'mods', 'config', '.fabric'], help='Files/directories to share between running instances.')
