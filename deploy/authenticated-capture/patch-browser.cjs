// Fix the pinned upstream release's guest-only incognito flag leaking into auth launches.
// No login, certificate, site-policy or account checks are bypassed.
const fs = require('node:fs');
const crypto = require('node:crypto');
const assert = require('node:assert/strict');
const path = '/app/core/meetings/services/bot/dist/capture-bridge.js';
const original = fs.readFileSync(path);
assert.equal(crypto.createHash('sha256').update(original).digest('hex'),
  '189abf51c9c35c2d9a0c1fdca5f34d46a5d0aed5d88adf830ff62befe99d0f1e',
  'Unexpected upstream browser code; refuse patching');
const before = 'const args = [...getAuthenticatedBrowserArgs(), ...getJoinBrowserArgs()];';
const after = 'const args = [...getAuthenticatedBrowserArgs(), ...getJoinBrowserArgs().filter(arg => !inv.authenticated || arg !== "--incognito")];';
const source = original.toString('utf8');
assert.equal(source.split(before).length, 2, 'Expected exactly one launch site');
// Evaluate the actual replacement against both modes before changing the image.
const launchArgs = new Function('inv', 'getAuthenticatedBrowserArgs', 'getJoinBrowserArgs',
  after + ' return args;');
const auth = () => ['--password-store=basic'];
const join = () => ['--incognito', '--autoplay-policy=no-user-gesture-required'];
assert.deepEqual(launchArgs({authenticated: true}, auth, join),
  ['--password-store=basic', '--autoplay-policy=no-user-gesture-required']);
assert.deepEqual(launchArgs({authenticated: false}, auth, join), [...auth(), ...join()]);
fs.writeFileSync(path, source.replace(before, after));
console.log('Applied and checked authenticated-session continuity fix for Vexa v0.12.28.');
