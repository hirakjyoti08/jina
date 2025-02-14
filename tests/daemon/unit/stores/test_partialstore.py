import asyncio
from pathlib import Path

import pytest

from daemon.models import FlowModel, PodModel
from daemon.stores.partial import PartialFlowStore, PartialPodStore, PartialStoreItem
from jina import Flow, __default_host__
from jina.helper import ArgNamespace
from jina.parsers import set_pod_parser
from jina.parsers.flow import set_flow_parser

cur_dir = Path(__file__).parent


@pytest.fixture()
def partial_pod_store():
    partial_pod_store = PartialPodStore()
    yield partial_pod_store
    partial_pod_store.delete()


@pytest.fixture()
def partial_flow_store():
    partial_flow_store = PartialFlowStore()
    yield partial_flow_store
    partial_flow_store.delete()


def test_podstore_add(partial_pod_store):
    partial_store_item = partial_pod_store.add(
        args=ArgNamespace.kwargs2namespace(PodModel().dict(), set_pod_parser()),
        envs={'key1': 'val1'},
    )
    assert partial_store_item
    assert partial_pod_store.object
    assert partial_store_item.arguments['runtime_cls'] == 'WorkerRuntime'
    assert partial_pod_store.object.env['key1'] == 'val1'
    assert partial_store_item.arguments['host_in'] == __default_host__
    assert partial_store_item.arguments['host'] == __default_host__


@pytest.mark.timeout(5)
def test_partial_podstore_delete(monkeypatch, mocker):
    close_mock = mocker.Mock()
    partial_store = PartialPodStore()

    partial_store.object = close_mock
    partial_store.delete()
    close_mock.close.assert_called()


def test_flowstore_add(monkeypatch, partial_flow_store):
    flow_model = FlowModel()
    flow_model.uses = f'{cur_dir}/flow.yml'
    args = ArgNamespace.kwargs2namespace(flow_model.dict(), set_flow_parser())
    partial_store_item = partial_flow_store.add(args, envs={'key1': 'val1'})

    assert partial_flow_store.object.env['key1'] == 'val1'
    assert partial_store_item
    assert isinstance(partial_flow_store.object, Flow)
    assert 'executor1' in partial_store_item.yaml_source
    assert partial_flow_store.object.port == 12345


@pytest.mark.asyncio
async def test_flowstore_rolling_update(partial_flow_store, mocker):
    flow_model = FlowModel()
    flow_model.uses = f'{cur_dir}/flow.yml'
    args = ArgNamespace.kwargs2namespace(flow_model.dict(), set_flow_parser())

    partial_flow_store.add(args)

    future = asyncio.Future()
    future.set_result(PartialStoreItem())
    mocker.patch(
        'daemon.stores.partial.PartialFlowStore.rolling_update', return_value=future
    )

    resp = await partial_flow_store.rolling_update(
        deployment_name='executor1', uses_with={}
    )
    assert resp


@pytest.mark.asyncio
async def test_flowstore_scale(partial_flow_store, mocker):
    flow_model = FlowModel()
    flow_model.uses = f'{cur_dir}/flow.yml'
    args = ArgNamespace.kwargs2namespace(flow_model.dict(), set_flow_parser())

    partial_flow_store.add(args)

    future = asyncio.Future()
    future.set_result(PartialStoreItem())
    mocker.patch('daemon.stores.partial.PartialFlowStore.scale', return_value=future)
    resp = await partial_flow_store.scale(deployment_name='executor1', replicas=2)
    assert resp
