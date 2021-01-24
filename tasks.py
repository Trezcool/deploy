from pathlib import Path

from invoke import Collection, task

from extra_tasks import lightsail


def _get_key_path(ctx, host):
    key_pair = ctx.lightsail.instances[host].key_pair
    return (Path('~') / '.ssh' / f'{key_pair}').expanduser()


@task
def bootstrap(ctx, host, user='ubuntu'):
    key_path = _get_key_path(ctx, host)
    ctx.run(f'ansible-playbook -i inventories/{host} -e host={host} -u {user} -b --private-key {key_path} bootstrap.yml')


@task
def deploy(ctx, host, user='ubuntu'):
    key_path = _get_key_path(ctx, host)
    ctx.run(f'ansible-playbook -i inventories/{host} -e host={host} -u {user} -b --private-key {key_path} play.yml')


@task
def debug(ctx, host):
    key_path = _get_key_path(ctx, host)
    ctx.run(f'ansible {host} -i inventories/{host} -u ubuntu --private-key {key_path} -m ping')
    # ctx.run(f'ansible {host} -i inventories/{host} -u ubuntu --private-key {key_path} -m shell -a "ls -la /"')

    # ctx.run(f'ansible {host} -i inventories/{host} --list-hosts')


ns = Collection(
    lightsail,

    bootstrap,
    deploy,
    debug
)
