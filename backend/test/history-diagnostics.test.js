import test from 'node:test';
import assert from 'node:assert/strict';
import { sealSession } from '../src/session-token.js';

test('history diagnostics requires a valid session and does not call the broker or disclose secrets', async () => {
  const previousEnv=process.env.NODE_ENV;
  const previousKey=process.env.SESSION_ENCRYPTION_KEY;
  process.env.NODE_ENV='test';
  process.env.SESSION_ENCRYPTION_KEY='b'.repeat(64);
  const { app } = await import('../src/server.js');
  const server=app.listen(0,'127.0.0.1');
  await new Promise(resolve=>server.once('listening',resolve));
  const url='http://127.0.0.1:'+server.address().port+'/api/diagnostics/history';
  try {
    const unauthorized=await fetch(url);
    assert.equal(unauthorized.status,401);
    const now=Date.now();
    const session={apiKey:'SENSITIVE_API_TEST',clientCode:'PRIVATE_CLIENT_TEST',
      jwt:'PRIVATE_TOKEN_TEST',createdAt:now,expiresAt:now+30*60_000};
    const id=sealSession(session);
    const response=await fetch(url,{headers:{'X-Session-Id':id}});
    assert.equal(response.status,200);
    assert.equal(response.headers.get('cache-control'),'no-store');
    const result=await response.json();
    assert.equal(result.ok,true);
    assert.equal(result.history.blocked,false);
    assert.equal(result.history.requestsLastHour,0);
    assert.equal(result.cache.total,0);
    assert.equal(result.quoteDataIndependent,true);
    const payload=JSON.stringify(result);
    for(const secret of [session.apiKey,session.clientCode,session.jwt,id]) {
      assert.ok(!payload.includes(secret),'history diagnostics must not expose any session secret');
    }
  } finally {
    await new Promise((resolve,reject)=>server.close(error=>error?reject(error):resolve()));
    if(previousEnv===undefined)delete process.env.NODE_ENV;else process.env.NODE_ENV=previousEnv;
    if(previousKey===undefined)delete process.env.SESSION_ENCRYPTION_KEY;else process.env.SESSION_ENCRYPTION_KEY=previousKey;
  }
});
