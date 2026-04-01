import streamlit as st
import csv
import anthropic
import json
import io

st.title("Rillet lead enrichment pipeline")
uploaded_file = st.file_uploader("Upload a CSV of companies", type="csv")

if uploaded_file:
    reader = csv.DictReader(io.StringIO(uploaded_file.getvalue().decode("utf-8")))
    companies = list(reader)
    st.write(f"Loaded {len(companies)} companies")
    st.dataframe(companies)

if st.button("Enrich Companies"):
        client = anthropic.Anthropic()
        results = []

        for c in companies:
            st.write(f"Enriching {c['company_name']}...")
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
            raw = response.content[0].text
            clean = raw.replace("```json", "").replace("```", "").strip()
            enriched = json.loads(clean)
            results.append(enriched)

        st.write("Done!")
        st.dataframe(results)