from . import ssh


def docker_exec(ctx, instance, container, ssh_user='ubuntu', user='root', cmd='ash'):  # ash (for alpine) | bash
    ssh(ctx, instance, user=ssh_user, cmd=f"'docker exec -it --user {user} {container} {cmd}'")


def docker_container_list(ctx, instance, all=False, ssh_user='ubuntu', user='root'):
    ssh(ctx, instance, user=ssh_user, cmd=f"'docker container ls {'-a' if all else ''}'")


def docker_logs(ctx, instance, container, ssh_user='ubuntu', since='24h'):
    ssh(ctx, instance, user=ssh_user, cmd=f"'docker logs --since {since} {container}'")


def docker_stats(ctx, instance, ssh_user='ubuntu', containers=''):
    ssh(ctx, instance, user=ssh_user, cmd=f"'docker stats {containers or '-a'}'")
