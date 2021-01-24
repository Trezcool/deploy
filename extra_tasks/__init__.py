from pathlib import Path

from dotenv import dotenv_values
from sshtunnel import SSHTunnelForwarder


def get_dotenv(instance):
    dotenv_path = Path('./env') / f'{instance}.env'
    if dotenv_path.exists():
        return dotenv_values(dotenv_path)


def ssh(ctx, instance, user='ubuntu', cmd=''):
    inst = ctx.lightsail.instances[instance]
    key_path = f'~/.ssh/{inst.key_pair}'
    ctx.run(
        f'ssh -t -o IdentityFile={key_path} -o ForwardAgent=yes {user}@{inst.fqdn} {cmd}',
        echo=True, pty=True
    )


def get_tunnel(host, port, user='ubuntu', keypair='id_rsa'):
    return SSHTunnelForwarder(
        (host, 22),
        ssh_username=user,
        ssh_pkey=f'~/.ssh/{keypair}',
        local_bind_address=('127.0.0.1',),
        remote_bind_address=(host, port),
    )
