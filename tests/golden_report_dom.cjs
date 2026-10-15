// Pure DOM-shim unit check: no browser control, network, or provider access.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const html = fs.readFileSync(process.argv[2], 'utf8');
const dataText = html.match(/<script id="report-data" type="application\/json">([\s\S]*?)<\/script>/)[1];
const data = JSON.parse(dataText);
assert.equal(data.golden.confusion.topic.columns_prediction.at(-1), '<missing>');
const code = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].at(-1)[1];
const elements = {};
const element = key => elements[key] ||= { innerHTML:'', textContent:'', value:'', handlers:{},
  addEventListener(type, handler){this.handlers[type] = handler;} };
element('#group').value = 'overall';
element('#field').value = 'topic';
const root = { querySelector: element };
const document = { getElementById(id){return id === 'golden-final-gate' ? root : { textContent:dataText };} };
vm.runInNewContext(code, { document, console });
assert.match(element('#accuracy tbody').innerHTML, /37\/50 \(74\.0%\)/);
assert.match(element('#recommendation').textContent, /not applied/);
const groups = { overall:data.golden, ...data.golden.by_fallback };
let checked = 0;
for (const [group, result] of Object.entries(groups)) {
  for (const [field, table] of Object.entries(result.confusion)) {
    element('#group').value = group;
    element('#field').value = field;
    element('#field').handlers.change();
    const shown = [...element('#confusion').innerHTML.matchAll(/<td[^>]*>(\d+)<\/td>/g)].map(m => Number(m[1]));
    assert.deepEqual(shown, table.counts.flat());
    assert.match(element('#matrix-source').textContent, new RegExp(`n=${result.agreement.topic.denominator} `));
    checked++;
  }
}
console.log(`PASS: ${checked} group/field confusion views reproduce source counts; group and field controls update rendering.`);
