from app.database import digest


def stage_login(client,username):
    result=client.write('POST','/stage/login',{'username':username,'password':username+'-local-2026'})
    assert result.status_code==200,result.text
    assert 'set-cookie' not in result.headers
    body=result.json()
    client.client.headers['Authorization']='Bearer '+body['access_token']
    client.client.headers['X-CSRF-Token']=body['csrf_token']
    return body


def test_stage_accounts_do_not_switch_cookie_and_bad_bearer_never_falls_back(harness):
    shared=harness.client('aoi')
    cookies=dict(shared.client.cookies)
    stage=stage_login(shared,'forest')
    assert dict(shared.client.cookies)==cookies
    assert shared.get('/me').json()['user']['username']=='forest'
    shared.client.headers['Authorization']='Bearer invalid'
    assert shared.get('/me').status_code==401
    shared.client.headers['Authorization']='Basic invalid'
    assert shared.get('/me').status_code==401
    del shared.client.headers['Authorization']
    assert shared.get('/me').json()['user']['username']=='aoi'
    shared.client.headers['Authorization']='Bearer '+stage['access_token']
    assert shared.write('POST','/logout').status_code==200
    assert shared.get('/me').status_code==401
    del shared.client.headers['Authorization']
    assert shared.get('/me').json()['user']['username']=='aoi'


def test_stage_two_memories_csrf_origin_expiry_and_token_type_isolation(harness):
    left,right=harness.client(),harness.client()
    aoi=stage_login(left,'aoi');forest=stage_login(right,'forest')
    assert left.get('/me').json()['user']['username']=='aoi'
    assert right.get('/me').json()['user']['username']=='forest'
    left.client.headers['X-CSRF-Token']=forest['csrf_token']
    assert left.write('POST','/communities',{'name':'混同','description':''}).status_code==403
    left.client.headers['X-CSRF-Token']=aoi['csrf_token']
    assert left.write('POST','/communities',{'name':'別起点','description':''},headers={'Origin':'https://invalid.test'}).status_code==403
    wrong=harness.client()
    wrong.client.cookies.set('ko_session',aoi['access_token'])
    assert wrong.get('/me').status_code==401
    with harness.app.state.database.transaction(True) as conn:
        conn.execute("UPDATE stage_sessions SET expires_at='2000-01-01T00:00:00+00:00' WHERE token_hash=?",(digest(aoi['access_token']),))
    assert left.get('/me').status_code==401
    assert right.get('/me').json()['user']['username']=='forest'


def test_stage_password_origin_and_frame_policy_are_explicit(harness):
    client=harness.client()
    assert client.write('POST','/stage/login',{'username':'forest','password':'wrong'}).status_code==401
    assert client.write('POST','/stage/login',{'username':'forest','password':'forest-local-2026'},headers={'Origin':'https://invalid.test'}).status_code==403
    # Response framing policy remains deny for API and absent static assets.
    response=client.get('/bootstrap')
    assert response.headers['x-frame-options']=='DENY'
    assert "frame-ancestors 'none'" in response.headers['content-security-policy']


def test_only_two_stage_html_paths_can_be_embedded(harness):
    import asyncio
    import httpx
    from starlette.responses import HTMLResponse
    from app.security import SecurityMiddleware

    async def html(scope,receive,send):
        await HTMLResponse('<main>local stage</main>')(scope,receive,send)

    async def check():
        app=SecurityMiddleware(html,harness.settings)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://localhost:8001') as client:
            for path in ('/stage/visitor','/stage/provider'):
                response=await client.get(path)
                assert response.headers['x-frame-options']=='SAMEORIGIN'
                assert "frame-ancestors 'self'" in response.headers['content-security-policy']
            for path in ('/','/stage','/stage/visitor/','/api/bootstrap'):
                response=await client.get(path)
                assert response.headers['x-frame-options']=='DENY'
    asyncio.run(check())
