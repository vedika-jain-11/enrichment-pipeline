import streamlit as st
import csv
import anthropic
import json
import io
import os
import requests

st.title("Rillet lead enrichment pipeline")

with st.sidebar:
    st.header("API Configuration")
    crustdata_token = st.secrets.get("CRUSTDATA_API_TOKEN", "") or os.environ.get("CRUSTDATA_API_TOKEN", "")
    crustdata_token = st.text_input(
        "Crustdata API Token",
        value=crustdata_token,
        type="password",
        help="Get this from your Crustdata dashboard. Or set CRUSTDATA_API_TOKEN env var.",
    )


def enrich_with_crustdata(domain: str, token: str) -> dict:
    url = "https://api.crustdata.com/screener/company"

    headers = {
        "Authorization": f"Token {token}",
        "Accept": "application/json",
    }

    params = {
        "company_domain": domain,
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        if isinstance(data, list) and len(data) > 0:
            company = data[0]
        elif isinstance(data, dict):
            company = data
        else:
            return {}

        return {
            "crustdata_employees": company.get("employee_count_range", "unknown"),
            "crustdata_linkedin_url": company.get("linkedin_profile_url", ""),
            "crustdata_founded_year": company.get("year_founded", "unknown"),
            "crustdata_revenue_lower": company.get("estimated_revenue_lower_bound_usd", "unknown"),
            "crustdata_revenue_upper": company.get("estimated_revenue_higher_bound_usd", "unknown"),
        }

    except requests.exceptions.RequestException as e:
        st.warning(f"Crustdata API error for {domain}: {e}")
        return {}


uploaded_file = st.file_uploader("Upload a CSV of companies", type="csv")

if uploaded_file:
    reader = csv.DictReader(io.StringIO(uploaded_file.getvalue().decode("utf-8")))
    companies = list(reader)
    st.write(f"Loaded {len(companies)} companies")
    st.dataframe(companies)

if st.button("Enrich Companies"):
    if not crustdata_token:
        st.error("Please enter your Crustdata API token in the sidebar.")
    else:
        client = anthropic.Anthropic()
        results = []
        progress = st.progress(0)

        for i, c in enumerate(companies):
            st.write(f"Enriching {c['company_name']}...")

            crustdata_info = enrich_with_crustdata(c["domain"], crustdata_token)

            if crustdata_info:
                context = (
                    f"Here is real data about this company from Crustdata:\n"
                    f"- Employees: {crustdata_info.get('crustdata_employees', 'unknown')}\n"
                    f"- Founded: {crustdata_info.get('crustdata_founded_year', 'unknown')}\n"
                    f"- Revenue (lower): ${crustdata_info.get('crustdata_revenue_lower', 'unknown')}\n"
                    f"- Revenue (upper): ${crustdata_info.get('crustdata_revenue_upper', 'unknown')}\n"
                )
            else:
                context = "No external data available for this company."

            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                messages=[
                    {"role": "user", "content": f"""You are a GTM research analyst. Analyze this company for fit with a modern AI-native ERP/accounting platform targeting high-growth startups.

Company: {c['company_name']}
Domain: {c['domain']}

{context}

Return ONLY a JSON object with these fields:
- company_name
- icp_fit_score (1-10, where 10 is perfect fit)
- icp_fit_reasoning (one sentence)
- suggested_outreach_angle (one sentence)
- pain_points (list of strings)
- likely_tech_stack (list of strings)

Respond with only the JSON, no markdown backticks or extra text."""}
                ],
            )

            raw = response.content[0].text
            clean = raw.replace("```json", "").replace("```", "").strip()
            claude_enriched = json.loads(clean)

            merged = {**crustdata_info, **claude_enriched}
            results.append(merged)

            progress.progress((i + 1) / len(companies))

        st.write("Done!")
        st.dataframe(results)
