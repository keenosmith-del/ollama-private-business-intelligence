"""Fixed SQL business facts. No model output is used in calculations."""
import re
from datetime import date
from decimal import Decimal
import psycopg


def quarter_start(year, quarter):
    return date(year, 3 * (quarter - 1) + 1, 1)


def next_quarter(start):
    return date(start.year + (start.month == 10), 1 if start.month == 10 else start.month + 3, 1)


def select_periods(question, latest):
    year_match = re.search(r'\b(20\d{2})\b', question)
    year = int(year_match.group()) if year_match else latest.year
    quarters = [int(a or b) for a, b in re.findall(r'\bq([1-4])\b|\bquarter\s*([1-4])\b', question.lower())]
    target = quarter_start(year, quarters[-1]) if quarters else quarter_start(year, (latest.month - 1) // 3 + 1)
    previous = quarter_start(target.year - (target.month == 1), 4 if target.month == 1 else (target.month - 1) // 3)
    if len(quarters) > 1: previous = quarter_start(year, quarters[0])
    return previous, target, quarters, year_match is not None


def financial_facts(database_url, org_id, question):
    q = question.lower()
    metrics, findings, sources, warnings = [], [], [], []
    with psycopg.connect(database_url) as conn:
        latest = conn.execute('SELECT max(sale_date) FROM sales WHERE org_id=%s', (org_id,)).fetchone()[0]
        if latest is None:
            latest = conn.execute('SELECT max(record_date) FROM financial_records WHERE org_id=%s', (org_id,)).fetchone()[0] or date.today()
        previous, target, quarters, explicit_year = select_periods(q, latest)
        trend = any(w in q for w in ['becoming less profitable', 'profitability declining', 'profit is declining', 'margin decline', 'margin drop'])
        comparison = len(quarters) > 1 or any(w in q for w in ['compare', 'decline', 'fall', 'fell', 'drop', 'change', 'quarter-over-quarter']) or trend
        start = previous if comparison else target
        end = next_quarter(target)
        scoped = bool(quarters) or comparison or explicit_year
        if explicit_year and not quarters and not comparison:
            start, end = date(target.year, 1, 1), date(target.year + 1, 1, 1)
        # All date predicates have explicit parameter values; the string is a fixed template.
        low, high = (start, end) if scoped else (date(1, 1, 1), date(9999, 12, 31))
        if any(w in q for w in ['revenue', 'sales', 'decline', 'quarter', 'q1', 'q2', 'q3', 'q4']):
            periods = [previous, target] if comparison else [target] if quarters else None
            rows = conn.execute("SELECT date_trunc('quarter',sale_date)::date,sum(amount) FROM sales WHERE org_id=%s GROUP BY 1 ORDER BY 1", (org_id,)).fetchall()
            totals = dict(rows)
            chosen = [(period, totals.get(period, Decimal(0))) for period in periods] if periods else [(d, v) for d, v in rows if not explicit_year or d.year == target.year]
            metrics.extend({'quarter': str(d), 'revenue': float(v)} for d, v in chosen)
            findings.append('Recorded revenue: ' + '; '.join(f'{d}: {v:.2f}' for d, v in chosen))
            if comparison:
                before, after = totals.get(previous, Decimal(0)), totals.get(target, Decimal(0))
                if before:
                    pct = ((after-before)/before*100).quantize(Decimal('0.01'))
                    metrics.append({'metric': f'q{(target.month-1)//3+1}_change_percent', 'value': float(pct)})
                    findings.append(f'Revenue change {previous} to {target}: {after-before:.2f} ({pct}%).')
                else: warnings.append('The comparison period has zero recorded revenue; percentage change is undefined.')
            if any(d not in totals for d, _ in chosen): warnings.append('An indicated quarter has no sales records; zero means no recorded revenue, not verified absence of activity.')
            sources.append({'type': 'dataset', 'name': 'sales', 'description': 'Sum of recorded sales; quarters shown explicitly'})
        if 'customer' in q:
            if trend:
                rows = conn.execute("""WITH s AS (SELECT customer_id,coalesce(sum(amount) FILTER(WHERE sale_date >= %s AND sale_date < %s),0) a,coalesce(sum(amount) FILTER(WHERE sale_date >= %s AND sale_date < %s),0) b FROM sales WHERE org_id=%s GROUP BY customer_id), f AS (SELECT customer_id,coalesce(sum(amount) FILTER(WHERE record_date >= %s AND record_date < %s),0) a,coalesce(sum(amount) FILTER(WHERE record_date >= %s AND record_date < %s),0) b FROM financial_records WHERE org_id=%s GROUP BY customer_id) SELECT c.name,s.a-coalesce(f.a,0),s.b-coalesce(f.b,0),s.b-coalesce(f.b,0)-s.a+coalesce(f.a,0) FROM customers c JOIN s ON s.customer_id=c.id LEFT JOIN f ON f.customer_id=c.id WHERE c.org_id=%s ORDER BY 4,c.name LIMIT 5""", (previous, next_quarter(previous), target, next_quarter(target), org_id, previous, next_quarter(previous), target, next_quarter(target), org_id, org_id)).fetchall()
                metrics.extend({'customer': r[0], 'q1Profit': float(r[1]), 'q2Profit': float(r[2]), 'change': float(r[3]), 'previousQuarter': str(previous), 'targetQuarter': str(target)} for r in rows)
                findings.append(f'Customer recorded gross profit movement {previous} to {target}: ' + str(metrics))
            elif any(w in q for w in ['profit', 'profitable', 'margin']):
                rows = conn.execute("""WITH s AS (SELECT customer_id,sum(amount) revenue FROM sales WHERE org_id=%s AND sale_date >= %s AND sale_date < %s GROUP BY customer_id), f AS (SELECT customer_id,sum(amount) costs FROM financial_records WHERE org_id=%s AND record_date >= %s AND record_date < %s GROUP BY customer_id) SELECT c.name,s.revenue,coalesce(f.costs,0),s.revenue-coalesce(f.costs,0),f.customer_id IS NOT NULL FROM customers c JOIN s ON s.customer_id=c.id LEFT JOIN f ON f.customer_id=c.id WHERE c.org_id=%s ORDER BY 4,c.name LIMIT 5""", (org_id, low, high, org_id, low, high, org_id)).fetchall()
                metrics.extend({'customer': r[0], 'revenue': float(r[1]), 'costs': float(r[2]), 'profit': float(r[3])} for r in rows)
                findings.append('Least recorded customer gross profit (revenue less attributed costs): ' + str(metrics))
                if any(not r[4] for r in rows): warnings.append('Some customers have no attributed costs. Their recorded profit is incomplete; shared overhead is excluded.')
            else:
                rows = conn.execute('SELECT c.name,sum(s.amount) FROM sales s JOIN customers c ON c.id=s.customer_id AND c.org_id=s.org_id WHERE s.org_id=%s AND sale_date >= %s AND sale_date < %s GROUP BY c.name ORDER BY 2 DESC,c.name LIMIT 5', (org_id, low, high)).fetchall()
                metrics.extend({'customer': r[0], 'revenue': float(r[1])} for r in rows)
                findings.append('Top customers by recorded revenue: ' + str([{'customer': r[0], 'revenue': float(r[1])} for r in rows]))
            sources.append({'type': 'dataset', 'name': 'sales and financial_records', 'description': f'Customer aggregates; {low} to {high} exclusive' if scoped else 'All recorded periods; attributed costs only, shared overhead excluded'})
        if 'profit' in q and 'customer' not in q:
            revenue = conn.execute('SELECT coalesce(sum(amount),0) FROM sales WHERE org_id=%s AND sale_date >= %s AND sale_date < %s', (org_id, low, high)).fetchone()[0]
            expenses = conn.execute('SELECT coalesce(sum(amount),0) FROM financial_records WHERE org_id=%s AND record_date >= %s AND record_date < %s', (org_id, low, high)).fetchone()[0]
            metrics.extend([{'metric':'recorded_revenue','value':float(revenue)}, {'metric':'recorded_expenses','value':float(expenses)}, {'metric':'recorded_profit','value':float(revenue-expenses)}])
            findings.append(f'Recorded revenue {revenue:.2f} less recorded expenses {expenses:.2f} = recorded profit {revenue-expenses:.2f}.')
            warnings.append('Profit covers recorded sales and expense entries only; it does not establish complete accounting or tax profit.')
            sources.extend([{'type':'dataset','name':'sales','description':'Recorded revenue sum'}, {'type':'dataset','name':'financial_records','description':'Recorded expense sum, aggregated separately to avoid duplicated amounts'}])
        if any(w in q for w in ['financial', 'cost', 'loss', 'expense', 'profitability']) and 'policy' not in q:
            limit = 3 if any(w in q for w in ['three', '3 biggest']) else 5
            rows = conn.execute('SELECT category,sum(amount) FROM financial_records WHERE org_id=%s AND record_date >= %s AND record_date < %s GROUP BY category ORDER BY 2 DESC,category LIMIT %s', (org_id, low, high, limit)).fetchall()
            metrics.extend({'category': r[0], 'amount': float(r[1])} for r in rows)
            findings.append('Largest recorded expense categories (cost exposure): ' + str([{'category': r[0], 'amount': float(r[1])} for r in rows]))
            if 'loss' in q: warnings.append('Expense totals are cost exposure, not proven financial losses. No causal loss amount has been calculated.')
            sources.append({'type': 'dataset', 'name': 'financial_records', 'description': 'Recorded expense category sums, not causal loss estimates'})
        if any(w in q for w in ['operational', 'incident', 'risk', 'issue']):
            rows = conn.execute('SELECT category,severity,count(*) FROM operational_records WHERE org_id=%s AND occurred_at >= %s AND occurred_at < %s GROUP BY category,severity ORDER BY 3 DESC,category LIMIT 10', (org_id, low, high)).fetchall()
            metrics.extend({'category': r[0], 'severity': r[1], 'count': r[2]} for r in rows)
            findings.append('Recorded operational incidents: ' + str([{'category': r[0], 'severity': r[1], 'count': r[2]} for r in rows]))
            sources.append({'type': 'dataset', 'name': 'operational_records', 'description': 'Incident frequency; no inferred financial impact'})
        if not metrics: warnings.append('No relevant structured records were found.')
    return metrics, findings, sources, warnings
