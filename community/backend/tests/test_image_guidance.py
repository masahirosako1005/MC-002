import builtins
import io
import json
import socket
from pathlib import Path

from app.config import Settings
from app.image_guidance import ImageGuidance, photo_guidance
from app.images import LocalClassifier
from app.main import create_app
from conftest import Client
from PIL import Image
from test_circles import accept_provider, circle, proposal_data, provider_invite, requirements


def photo():
    stream=io.BytesIO()
    Image.new('RGB',(48,48),(35,92,160)).save(stream,'PNG')
    return stream.getvalue()


def ok(response):
    assert response.status_code==200,response.text
    return response.json()


def test_guidance_only_matches_exact_known_assets_and_does_not_score():
    root=Path(__file__).resolve().parents[2]
    for name,expected in [('woodland',{'mountain','nature','cafe'}),('coffee',{'cafe','food'}),('coast',{'coast','walk'}),('table',{'food','games','stay'})]:
        result=photo_guidance((root/'assets'/f'{name}.png').read_bytes())
        assert result['status']=='guided' and result['method']=='predefined-photo-tags-v1'
        assert {tag['id'] for tag in result['tags']}==expected
        assert all(set(tag)=={'id','label'} for tag in result['tags'])
        assert result['model_version'] is None and not result['inference_enabled']
    arbitrary=photo_guidance(photo())
    assert arbitrary['status']=='manual' and arbitrary['tags']==[]
    assert arbitrary['method']=='manual-photo-tags-v1'


def test_normal_start_never_constructs_model_or_imports_inference_and_needs_no_network(harness,tmp_path,monkeypatch):
    imports=[]
    original_import=builtins.__import__
    def guarded_import(name,*args,**kwargs):
        if name.split('.')[0] in ('onnxruntime','numpy','openai','anthropic'):
            imports.append(name)
            raise AssertionError('Normal runtime attempted inference import')
        return original_import(name,*args,**kwargs)
    def blocked(*_args,**_kwargs):
        raise AssertionError('Normal runtime attempted model or network access')
    monkeypatch.setattr(builtins,'__import__',guarded_import)
    monkeypatch.setattr(LocalClassifier,'__init__',blocked)
    monkeypatch.setattr(socket,'create_connection',blocked)
    for key in ('OPENAI_API_KEY','ANTHROPIC_API_KEY','MODEL_DIR'):
        monkeypatch.delenv(key,raising=False)
    # Even a caller's old worker=True setting must not activate real inference.
    settings=Settings(db_path=tmp_path/'normal.db',media_dir=tmp_path/'media',model_dir=tmp_path/'absent-model',worker_enabled=True)
    app=create_app(settings)
    life=app.router.lifespan_context(app)
    harness.runner.run(life.__aenter__())
    client=Client(harness.runner,app)
    try:
        assert ok(client.get('/health'))['status']=='ok'
        model=ok(client.get('/bootstrap'))['model']
        assert model['status']=='guided' and not model['inference_enabled'] and not model['external_ai_enabled']
        assert isinstance(app.state.classifier,ImageGuidance)
        assert not app.state.worker.thread.is_alive()
        assert not app.state.worker.once()
        assert imports==[] and not settings.model_dir.exists()
        client.login('aoi')
        media=ok(client.request('POST','/media',files={'file':('coast.png',photo(),'image/png')}))
        assert media['analysis']['status']=='manual' and media['analysis']['tags']==[]
    finally:
        client.close()
        harness.runner.run(life.__aexit__(None,None,None))


def test_manual_upload_finishes_immediately_and_user_can_select_publish_tags(harness):
    client=harness.client('aoi')
    before=ok(client.get('/me/preferences'))
    media=ok(client.request('POST','/media',files={'file':('woodland.png',photo(),'image/png')}))
    assert media['analysis']['status']=='manual' and media['analysis']['tags']==[]
    assert media['analysis']['model_version'] is None and not media['analysis']['inference_enabled']
    assert ok(client.get('/me/preferences'))==before
    retry=ok(client.write('POST','/media/'+media['id']+'/analyze'))
    assert retry['status']=='manual' and retry['tags']==[]
    created=ok(client.write('POST','/posts',dict(community_id='peers',body='自分で選んだ写真',media_ids=[media['id']],tags=['walk'])))
    published=ok(client.write('PATCH','/posts/'+created['id'],dict(status='published',tags=['walk'])))
    assert published['status']=='published' and published['tags']==['walk']
    ren=harness.client('ren')
    shown=next(item for item in ok(ren.get('/communities/peers/feed'))['items'] if item['id']==created['id'])
    assert shown['tags']==['walk'] and shown['media'][0]['analysis']['tags']==[]


def test_saved_jobs_are_projected_to_terminal_manual_without_rewriting_old_values(harness):
    client=harness.client('aoi')
    media=ok(client.request('POST','/media',files={'file':('photo.png',photo(),'image/png')}))
    for status in ('queued','running','succeeded','failed'):
        with harness.app.state.database.transaction(True) as conn:
            conn.execute('UPDATE jobs SET status=?,tags=?,model_version=?,message=? WHERE media_id=?',(status,json.dumps([dict(id='coast',label='海辺',score=.42)]),'historical-model','以前の保存結果',media['id']))
            before=tuple(conn.execute('SELECT * FROM jobs WHERE media_id=?',(media['id'],)).fetchone())
        result=ok(client.get('/media/'+media['id']+'/analysis'))
        assert result['status']=='manual' and result['method']=='saved-candidates-manual-review'
        assert result['tags'][0]['score']==.42 and result['model_version']=='historical-model'
        assert not result['inference_enabled']
        assert ok(client.write('POST','/media/'+media['id']+'/analyze'))==result
        assert not harness.app.state.worker.once()
        with harness.app.state.database.transaction() as conn:
            assert tuple(conn.execute('SELECT * FROM jobs WHERE media_id=?',(media['id'],)).fetchone())==before


def test_local_conditions_candidate_invitation_and_confirmations_remain_real(harness,monkeypatch):
    def no_network(*_args,**_kwargs):
        raise AssertionError('External network is not permitted')
    monkeypatch.setattr(socket,'create_connection',no_network)
    aoi,forest=harness.client('aoi'),harness.client('forest')
    created=circle(aoi)
    pid=created['id']
    turn=ok(aoi.write('POST','/circles/'+pid+'/assistant-turns',dict(body='6人で森に行きたい。2泊、1人3万円、プラン部分。2027年3月1日。',client_request_id='guided-turn')))
    assert turn['proposed_conditions']['planned_people']==6
    help=ok(aoi.get('/circles/help'))
    assert not help['external_ai_enabled']
    requirements(aoi,pid)
    card=ok(aoi.write('POST','/circles/'+pid+'/candidate-cards',dict(plan_id='forest-six',plan_version=1,client_request_id='candidate')))
    assert ok(aoi.get('/circles/'+pid+'/candidate-cards'))['items'][0]['id']==card['id']
    invite,_=provider_invite(aoi,pid)
    assert invite['status']=='pending'
    accept_provider(forest,invite)
    proposal=ok(forest.write('POST','/circle-provider-invitations/'+invite['id']+'/proposals',proposal_data()))
    for client,key in ((aoi,'traveler-confirm'),(forest,'provider-confirm')):
        ok(client.write('POST','/circle-provider-invitations/'+invite['id']+'/confirmations',dict(proposal_id=proposal['id'],version=proposal['version'],client_request_id=key)))
    current=ok(aoi.get('/circle-provider-invitations/'+invite['id']+'/room'))
    assert current['proposal']['status']=='both_confirmed'
    assert current['reservation_status']=='not_booked'


def test_deleted_photo_cleanup_retries_at_start_without_inference_and_keeps_live_media(harness,monkeypatch):
    aoi=harness.client('aoi')
    deleted=ok(aoi.request('POST','/media',files={'file':('photo.png',photo(),'image/png')}))
    active=ok(aoi.request('POST','/media',files={'file':('keep.png',photo(),'image/png')}))
    post=ok(aoi.write('POST','/posts',dict(community_id='peers',body='削除対象',media_ids=[deleted['id']],tags=['walk'])))
    target=harness.settings.media_dir/(deleted['id']+'.jpg')
    original_unlink=Path.unlink
    def fail_once(path,*args,**kwargs):
        if path==target:
            raise PermissionError('Temporary fixture lock')
        return original_unlink(path,*args,**kwargs)
    with monkeypatch.context() as blocked:
        blocked.setattr(Path,'unlink',fail_once)
        ok(aoi.write('DELETE','/posts/'+post['id']))
        assert target.exists()
        assert aoi.get('/media/'+deleted['id']).status_code==404
    restarted=create_app(harness.settings)
    lifecycle=restarted.router.lifespan_context(restarted)
    harness.runner.run(lifecycle.__aenter__())
    try:
        assert not target.exists()
        assert (harness.settings.media_dir/(active['id']+'.jpg')).exists()
        assert not restarted.state.worker.thread.is_alive()
        assert restarted.state.classifier.session is None
    finally:
        harness.runner.run(lifecycle.__aexit__(None,None,None))
