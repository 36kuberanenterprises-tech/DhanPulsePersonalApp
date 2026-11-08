import test from 'node:test';
import assert from 'node:assert/strict';

test('login readiness checks required configuration without exposing credentials', async () => {
  const names = ['ANGEL_API_KEY', 'ANGEL_CLIENT_CODE', 'SESSION_ENCRYPTION_KEY'];
  const previous = Object.fromEntries(names.map(name => [name, process.env[name]]));
  const previousNodeEnv = process.env.NODE_ENV;
  process.env.NODE_ENV = 'test';

  const { app } = await import('../src/server.js');
  const server = app.listen(0, '127.0.0.1');
  await new Promise(resolve => server.once('listening', resolve));
  const url = 'http://127.0.0.1:' + server.address().port + '/api/auth/readiness';

  try {
    delete process.env.ANGEL_API_KEY;
    delete process.env.ANGEL_CLIENT_CODE;
    delete process.env.SESSION_ENCRYPTION_KEY;

    let response = await fetch(url);
    let body = await response.json();
    assert.equal(response.status, 200);
    assert.equal(body.loginReady, false);
    assert.equal(body.status, 'LOGIN_CONFIGURATION_INCOMPLETE');

    process.env.ANGEL_API_KEY = 'sample-test-api-key';
    process.env.ANGEL_CLIENT_CODE = 'sample-client-code';
    process.env.SESSION_ENCRYPTION_KEY = 'a'.repeat(64);
    response = await fetch(url);
    body = await response.json();
    assert.equal(response.status, 200);
    assert.equal(body.loginReady, true);
    assert.equal(body.status, 'READY');
    assert.equal(response.headers.get('cache-control'), 'no-store');
    const output = JSON.stringify(body);
    assert.equal(output.includes('sample-test-api-key'), false);
    assert.equal(output.includes('sample-client-code'), false);
    assert.equal(output.includes('a'.repeat(64)), false);

    process.env.SESSION_ENCRYPTION_KEY = 'invalid';
    response = await fetch(url);
    body = await response.json();
    assert.equal(body.loginReady, false);
  } finally {
    await new Promise((resolve, reject) => server.close(error => error ? reject(error) : resolve()));
    for (const name of names) {
      if (previous[name] === undefined) delete process.env[name];
      else process.env[name] = previous[name];
    }
    if (previousNodeEnv === undefined) delete process.env.NODE_ENV;
    else process.env.NODE_ENV = previousNodeEnv;
  }
});
