# Copyright 2021 Fluence Labs Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__             import with_statement
from fabric.contrib.files   import append
from fabric.api   import *
from fabric.utils import *
import json
import time
import yaml
import copy

CONFIG = {
    'services': {
        'fluence': {
            'environment': {
                'RUST_BACKTRACE': 'full',
                'WASM_LOG': 'info',
                'RUST_LOG': 'info,network=trace,execution=trace,tide=warn,aquamarine=info,aquamarine::actor=info,tokio_threadpool=info,tokio_reactor=info,mio=info,tokio_io=info,soketto=info,yamux=info,multistream_select=info,libp2p_secio=info,libp2p_websocket::framed=info,libp2p_ping=info,libp2p_core::upgrade::apply=info,libp2p_kad::kbucket=info,cranelift_codegen=info,wasmer_wasi=info,async_io=info,polling=info,wasmer_interface_types_fl=info ,cranelift_codegen=info,wasmer_wasi=info,async_io=info,polling=info,wasmer_interface_types_fl=info,particle_server::behaviour::identify=info,libp2p_mplex=info,libp2p_identify=info,walrus=info,particle_protocol::libp2p_protocol::upgrade=info',
                'IPFS_ADDRESSES_ANNOUNCE': '/ip4/{host}/tcp/{ipfs_swarm_port},/ip4/{host}/tcp/{ipfs_swarm_port}/ws',
                'FLUENCE_ENV_AQUA_IPFS_EXTERNAL_API_MULTIADDR': '/ip4/{host}/tcp/{ipfs_port}',
                'CERAMIC_HOST': '{ceramic_host}',
            },
            'command': '-c /Config.toml -f ed25519 -k {keypair} -x {host} -t {tcp_port} -w {ws_port} -m {management_key}',
            'volumes': [
                '{container_name}:/.fluence',
                '{container_name}_config:/config',
            ],
            'container_name': '{container_name}',
            'image': '{container_image}',
            'ports': [
                '{tcp_port}:{tcp_port}',
                '{ws_port}:{ws_port}',
                '{ipfs_port}:5001',
                '{ipfs_swarm_port}:4001',
                '{ipfs_gateway_port}:8080',
                '{metrics_port}:18080'
            ],
            'restart': 'always'
        }
    },
    'version': '3.5',
    'volumes': {
        '{container_name}': None,
        '{container_name}_config': None,
    }
}

def gen_compose_file(out, container_image, scale, is_bootstrap, bootstraps, host, management_key, keypairs, ceramic_host):
    assert len(container_image) > 0, "container image must not be empty, was: '{}'".format(container_image)

    if is_bootstrap == True:
        container = 'fluence_bootstrap'
        tcp_port = 7770
        ws_port = 9990
        ipfs_port = 5550
        ipfs_swarm_port = 4440
        ipfs_gateway_port = 8880
        metrics_port = 28880
    else:
        container = 'fluence'
        tcp_port = 7001
        ws_port = 9001
        ipfs_port = 5001
        ipfs_swarm_port = 4001
        ipfs_gateway_port = 8001
        metrics_port = 28081


    config = copy.deepcopy(CONFIG)
    service = config['services']['fluence']
    del config['services']['fluence']
    config['volumes'] = {}

    for i in range(0, scale):
        container_name = container + '-{}'.format(i)

        config['services'][container_name] = copy.deepcopy(service)
        container_config = config['services'][container_name]

        container_config['container_name'] = container_name
        container_config['image'] = container_image.encode('utf-8')
        container_config['volumes'] = map(
            lambda v: v.format(container_name=container_name),
            container_config['volumes']
        )

        container_config['command'] = container_config['command'].format(
            keypair=keypairs[i],
            management_key=management_key,
            host=host,
            tcp_port=tcp_port,
            ws_port=ws_port
        )
        if len(bootstraps) > 0:
            container_config['command'] += ' --bootstraps {}'.format(' '.join(bootstraps))

        container_config['ports'] = map(lambda p: p.format(
            tcp_port=tcp_port,
            ws_port=ws_port,
            ipfs_port=ipfs_port,
            ipfs_swarm_port=ipfs_swarm_port,
            ipfs_gateway_port=ipfs_gateway_port,
            metrics_port=metrics_port
        ), container_config['ports'])

        for key in container_config['environment']:
            container_config['environment'][key] = container_config['environment'][key].format(
                host=host,
                ipfs_port=ipfs_port,
                ipfs_swarm_port=ipfs_swarm_port,
                ipfs_gateway_port=ipfs_gateway_port,
                ceramic_host=ceramic_host,
            )

        for key in CONFIG['volumes']:
            key = key.format(container_name=container_name)
            config['volumes'][key] = None

        tcp_port += 1
        ws_port += 1
        ipfs_port += 1
        ipfs_swarm_port += 1
        ipfs_gateway_port += 1
        metrics_port += 1

    puts("Writing config to {}".format(out))
    with hide('running'):
        run('rm {} || true'.format(out))
        append(out, yaml.dump(config))

