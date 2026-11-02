import argparse
from alembic.config import Config
from alembic import command
from app.nexus.seed import seed

if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--migrate-only', action='store_true', help='Upgrade schema without changing seed accounts')
    args = parser.parse_args()
    command.upgrade(Config('alembic-nexus.ini'),'head')
    if args.migrate_only:
        print('Nexus schema ready; existing accounts unchanged')
    else:
        created, refreshed = seed()
        print('Nexus schema and seed accounts ready')
        print('created: ' + (', '.join(created) or 'none'))
        print('refreshed: ' + (', '.join(refreshed) or 'none'))
