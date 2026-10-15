"""Render existing evaluation and separately frozen development evidence offline."""
import json
from pathlib import Path


def render():
    output = Path('evals/golden-final-evaluation')
    golden = json.loads((output/'report.json').read_text(encoding='utf-8'))
    development = json.loads(Path('docs/fallback-options-development.json').read_text(encoding='utf-8'))
    accounting = json.loads(Path('docs/pre-100k-accounting-snapshot.json').read_text(encoding='utf-8'))
    measured = json.loads(Path('artifacts/golden-final/measurements.json').read_text(encoding='utf-8'))
    if development.get('golden_accuracy_used') is not False or development['recommendation']['status']!='proposal only; not applied':
        raise ValueError('Development recommendation provenance unavailable')
    aggregate = {key:value for key,value in golden.items() if key not in {'disagreements'}}
    data = {'golden':aggregate,'development':development,
            'execution':{'calls':accounting['golden_call_count'],'cost':sum(accounting['golden_cost_by_provider_usd'].values()),
                         'seconds':measured['wall_seconds'],'project_spend':accounting['ledger_spent_usd'],
                         'openai_local':accounting['accounted_by_provider_usd']['openai']}}
    template = Path('reports/golden-final-template.html').read_text(encoding='utf-8')
    html = template.replace('__GOLDEN_DATA__',json.dumps(data,ensure_ascii=False).replace('<',chr(92)+'u003c'))
    (output/'report.html').write_text(html,encoding='utf-8')
    return output/'report.html'


if __name__=='__main__':
    print(render())
