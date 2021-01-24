from pprint import pprint

import boto3
from invoke import task, Collection

import extra_tasks._docker as docker
import extra_tasks._postgres as pg
from . import get_dotenv, ssh as _ssh


def get_client(ctx, instance=None):
    if instance:
        region = ctx.lightsail.instances[instance].get('region')
        key_id = secret_key = None

        dotenv = get_dotenv(instance)
        if dotenv:
            key_id = dotenv.get('AWS_ACCESS_KEY_ID')
            secret_key = dotenv.get('AWS_SECRET_ACCESS_KEY')

        return boto3.client('lightsail', region_name=region, aws_access_key_id=key_id, aws_secret_access_key=secret_key)

    return boto3.client('lightsail')


@task
def add_admin_email(ctx, email='kambembotresor@gmail.com'):
    client = get_client(ctx)
    # add
    res = client.create_contact_method(protocol='Email', contactEndpoint=email)
    print('add_status: ', res['operations'][0]['status'])
    # verify
    res = client.send_contact_method_verification(protocol='Email')
    print('verify_status: ', res['operations'][0]['status'])


@task
def get_default_key_pair(ctx):
    pprint(get_client(ctx).download_default_key_pair())


@task
def create_key_pair(ctx, name):
    pprint(get_client(ctx).create_key_pair(name))


@task
def create(ctx, instance):
    inst = ctx.lightsail.instances[instance]
    res = get_client(ctx, instance).create_instances(
        instanceNames=[instance],
        availabilityZone=inst.az,
        blueprintId=inst.blueprint_id,
        bundleId=inst.bundle_id,
        keyPairName=inst.key_pair
    )
    print('create_status: ', res['operations'][0]['status'])


@task
def setup_firewall(ctx, instance):
    defaults = [
        {'port': 22},
        {'port': 80},
        {'port': 443},
    ]
    rules = ctx.lightsail.instances[instance].get('firewall_rules', defaults)
    port_infos = []
    for rule in rules:
        info = {
            'fromPort': rule['port'],
            'toPort': rule['port'],
            'protocol': rule.get('proto', 'tcp'),
        }
        if 'cidrs' in rule:
            info['cidrs'] = rule['cidrs']
        port_infos.append(info)

    res = get_client(ctx, instance).put_instance_public_ports(portInfos=port_infos, instanceName=instance)
    print('firewall_status: ', res['operation']['status'])


@task
def create_static_ip(ctx, instance):
    client = get_client(ctx, instance)
    # allocate
    name = f'{instance}-StaticIp'
    res = client.allocate_static_ip(staticIpName=name)
    print('allocate_status: ', res['operations'][0]['status'])
    # attach
    res = client.attach_static_ip(staticIpName=name, instanceName=instance)
    print('attach_status: ', res['operations'][0]['status'])
    # summary
    pprint(client.get_static_ip(staticIpName=name))


# todo: based on 2-week historical data...
# https://lightsail.aws.amazon.com/ls/docs/en_us/articles/amazon-lightsail-adding-instance-health-metric-alarms
@task
def setup_alarms(ctx, instance):
    client = get_client(ctx, instance)
    # BurstCapacityPercentage , BurstCapacityTime , CPUUtilization , NetworkIn , NetworkOut , StatusCheckFailed ,
    # StatusCheckFailed_Instance, StatusCheckFailed_System
    # todo: thresh - 80 | 10 % of bundle
    defaults = [
        {'name': 'cpu-up', 'metric': 'CPUUtilization', 'op': 'GreaterThanOrEqualToThreshold', 'thresh': 0, 'period': 1},
        {'name': 'cpu-down', 'metric': 'CPUUtilization', 'op': 'LessThanOrEqualToThreshold', 'thresh': 0, 'period': 1},
    ]
    for alarm in defaults:
        res = client.put_alarm(
            alarmName=alarm['name'],
            metricName=alarm['metric'],
            monitoredResourceName=instance,
            comparisonOperator=alarm['op'],
            threshold=alarm['thresh'],
            evaluationPeriods=alarm['period'],  # 1 = 5 min rolling period
            datapointsToAlarm=123,  # todo: rm ?
            contactProtocols=['Email'],
            notificationTriggers=['ALARM']
        )
        print(f'{alarm["name"]} status: ', res['operations'][0]['status'])


@task
def init(ctx, instance):
    # create(ctx, instance)
    setup_firewall(ctx, instance)
    create_static_ip(ctx, instance)


@task
def ssh(ctx, instance, user='ubuntu', cmd=''):
    _ssh(ctx, instance, user, cmd)


@task
def proxy_to_port(ctx, instance, port, local_port=None, user='ubuntu'):
    local_port = local_port or port
    inst = ctx.lightsail.instances[instance]
    key_path = f'~/.ssh/{inst.key_pair}'
    ssh_cmd = f'ssh -o IdentityFile={key_path} {user}@{inst.fqdn} -L {local_port}:localhost:{port} -N'
    print(ssh_cmd)
    ctx.run(ssh_cmd, pty=True)


@task
def scp_from_vm(ctx, instance, remote_path, user='ubuntu'):
    inst = ctx.lightsail.instances[instance]
    key_path = f'~/.ssh/{inst.key_pair}'
    ctx.run(
        f'scp -r -o IdentityFile={key_path} -o ForwardAgent=yes {user}@{inst.fqdn}:{remote_path} ./',
        pty=True, echo=True
    )


ns = Collection(
    add_admin_email,
    get_default_key_pair, create_key_pair,

    init,
    create,
    setup_firewall,
    create_static_ip,
    setup_alarms,

    ssh,
    proxy_to_port,
    scp_from_vm,

    task(docker.docker_exec),
    task(docker.docker_container_list),
    task(docker.docker_logs),
    task(docker.docker_stats),

    task(pg.psql),
    task(pg.psql_db_list),
    task(pg.psql_user_list),
    task(pg.pg_create_user),
    task(pg.pg_drop_user),
    task(pg.pg_create_db),
    task(pg.pg_drop_db),
    task(pg.pg_enable_extension),
    task(pg.pg_dump),
    task(pg.pg_restore),
)
