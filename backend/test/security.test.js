import test from 'node:test';
import assert from 'node:assert/strict';
process.env.DATABASE_URL??='postgresql://unused:unused@localhost:5432/unused';
process.env.JWT_SECRET??='unit-test-secret-at-least-32-characters-long';
process.env.AI_INTERNAL_TOKEN??='unit-test-internal-token-at-least-32-characters';
const {allow,authenticate}=await import('../dist/security.js');
function response(){return {statusCode:200,status(code){this.statusCode=code;return this},json(value){this.body=value;return this}}}
test('analyst is permitted by analyst role gate',()=>{let passed=false;const req={principal:{role:'analyst'}};allow('admin','analyst')(req,response(),()=>{passed=true});assert.equal(passed,true)});
test('viewer is denied document upload role gate',()=>{const res=response();allow('admin','analyst')({principal:{role:'viewer'}},res,()=>{});assert.equal(res.statusCode,403)});
test('missing bearer token is rejected',()=>{const res=response();authenticate({headers:{}},res,()=>{});assert.equal(res.statusCode,401)});
