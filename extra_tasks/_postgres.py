import datetime
import os

from fabric.contrib.console import confirm

from . import get_dotenv, get_tunnel


def _prep_cmd(prog, opts='', args=''):
    cmd = f'{prog} {opts}'
    return cmd + ' {defaults} ' + args


def pg_exec(ctx, instance, cmd, user=None, passwd=None, warn=False):
    dotenv = get_dotenv(instance)
    if dotenv:
        user = user or dotenv.get('POSTGRES_ADMIN_USER')
        passwd = passwd or dotenv.get('POSTGRES_ADMIN_PASSWORD')

    inst = ctx.lightsail.instances[instance]
    with get_tunnel(host=inst.fqdn, port=5432, keypair=inst.key_pair) as tunnel:
        cmd = cmd.format(defaults=f'--host=127.0.0.1 --port={tunnel.local_bind_port} --username={user}')
        if warn:
            if confirm(f'Executing following pg cmd...\n{cmd}\n --- proceed?'):
                ctx.run(cmd, env={'PGPASSWORD': passwd})
        else:
            ctx.run(cmd, echo=True, pty=True, env={'PGPASSWORD': passwd})


def psql(ctx, instance, user=None, passwd=None, db='postgres'):
    cmd = _prep_cmd('psql', args=db)
    pg_exec(ctx, instance, cmd, user, passwd)


def psql_db_list(ctx, instance, user=None, passwd=None):
    cmd = _prep_cmd('psql', opts='-l')
    pg_exec(ctx, instance, cmd, user, passwd)


def psql_user_list(ctx, instance, user=None, passwd=None):
    cmd = _prep_cmd('psql', opts='-c "\\dgd"', args='postgres')
    pg_exec(ctx, instance, cmd, user, passwd)


def pg_create_user(ctx, instance, user, passwd, admin_user=None, admin_passwd=None):
    # NB: must run as admin
    sql = f'CREATE USER \\"{user}\\" CREATEDB ENCRYPTED PASSWORD \'{passwd}\';'
    cmd = _prep_cmd('psql', opts=f'-c "{sql}"', args='postgres')
    pg_exec(ctx, instance, cmd, user=admin_user, passwd=admin_passwd, warn=True)


def pg_drop_user(ctx, instance, user, admin_user=None, admin_passwd=None):
    # NB: must run as admin
    cmd = _prep_cmd('dropuser', args=user)
    pg_exec(ctx, instance, cmd, user=admin_user, passwd=admin_passwd, warn=True)


def pg_create_db(ctx, instance, user, passwd, db):
    # NB: Must run as app user created by `pg_create_user`
    cmd = _prep_cmd('createdb', args=db)
    pg_exec(ctx, instance, cmd, user, passwd, warn=True)


def pg_drop_db(ctx, instance, user, passwd, db):
    # NB: Must run as app user created by `pg_create_user`
    cmd = _prep_cmd('dropdb', args=db)
    pg_exec(ctx, instance, cmd, user, passwd, warn=True)


def pg_enable_extension(ctx, instance, extension, db, admin_user=None, admin_passwd=None):
    # NB: must run as admin
    sql = f'CREATE EXTENSION IF NOT EXISTS {extension};'
    cmd = _prep_cmd('psql', opts=f'-c "{sql}"', args=db)
    pg_exec(ctx, instance, cmd, admin_user, admin_passwd, warn=True)


def pg_dump(ctx, instance, db, user=None, passwd=None):
    date = datetime.date.today().strftime('%Y%m%d')
    filename = f'{db}.{date}.pgdump'
    cmd = _prep_cmd('pg_dump', opts=f'--no-owner --no-privileges --file={filename}', args=db)
    pg_exec(ctx, instance, cmd, user=user, passwd=passwd, warn=True)


def pg_restore(ctx, instance, file, db, user=None, passwd=None):
    if not os.path.exists(os.path.expanduser(file)):
        print('Db dump not found:', file)
        exit(1)

    cmd = _prep_cmd('pg_restore', opts=f'--no-owner --no-privileges --dbname={db}', args=file)
    pg_exec(ctx, instance, cmd, user=user, passwd=passwd, warn=True)
