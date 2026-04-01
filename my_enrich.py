import csv
import anthropic
import json

companies = []
with open("sample_companies.csv", "r") as f:
    reader = csv.DictReader(f)
    for row in reader:
        companies.append(row)

for company in companies:
    print(company["company_name"])

client = anthropic.Anthropic()

results = []

for c in companies:
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[
            {"role": "user", "content": f"""Can you please return a JSON that takes {c['company_name']} at {c['domain']} and returns:
            - company_name
            - stage (seed, series_a, series_b, etc.)
            - estimated_employees
            - icp_fit_score (1-10)
            - pain_points (a list)
            - suggested_outreach_angle
             Respond only with a JSON.
            """}
        ]
    )
    print(response.content[0].text)
    raw = response.content[0].text
    clean = raw.replace("```json", "").replace("```", "").strip()
    enriched = json.loads(clean)
    #print(enriched["company_name"], enriched["icp_fit_score"])
    results.append(enriched)

with open("enriched_output.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=results[0].keys())
    writer.writeheader()
    for r in results:
        row = {}
        for key in r:
            value = r[key]
            if isinstance(value, list):
                value = "; ".join(str(v) for v in value)
            row[key] = value
        writer.writerow(row)    