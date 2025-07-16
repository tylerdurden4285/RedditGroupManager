import json
import pytest


def test_delete_group_sets_hx_trigger(app, group_manager):
    with app.app_context():
        group_id = group_manager.create_group('Toast Group', 'desc', [{'subreddit': 'python'}])
    client = app.test_client()
    resp = client.delete(f'/groups/delete/{group_id}', headers={'HX-Request': 'true'})
    assert resp.status_code == 200
    header = resp.headers.get('HX-Trigger')
    assert header
    data = json.loads(header)
    assert data['toast']['category'] == 'success'
    assert 'deleted successfully' in data['toast']['message']


