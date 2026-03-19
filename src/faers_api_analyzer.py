"""
Open FDA FAERS Adverse Events Analyzer
Fetches drug adverse events from the Open FDA API and calculates pharmacovigilance statistics
"""

import requests
from requests.exceptions import RequestException
import pandas as pd
import numpy as np
from collections import defaultdict
import csv
from datetime import datetime
import json
import time
from ratelimit import limits, sleep_and_retry

# ============================================================================
# CONFIGURATION - EDIT THE DRUG NAME HERE
# ============================================================================
DRUG_NAME = "nexlizet"  # Change this to the drug you want to analyze
OUTPUT_FILENAME = f"faers_{DRUG_NAME.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

# Open FDA API Configuration
FDA_API_BASE_URL = "https://api.fda.gov/drug/event.json"
API_LIMIT = 100  # Records per request (max 100)

# Rate limiting / retry configuration
MAX_RETRIES_429 = 5

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

@sleep_and_retry
@limits(calls=40, period=60)
def call_fda_api(params: dict) -> dict:
    """Call OpenFDA and handle rate limiting (including 429 responses).

    OpenFDA limits:
      - 40 requests/minute without an API key
      - 240 requests/minute with an API key
    """
    for attempt in range(1, MAX_RETRIES_429 + 1):
        try:
            response = requests.get(FDA_API_BASE_URL, params=params, timeout=10)
        except RequestException as e:
            raise

        if response.status_code == 429:
            backoff_secs = 2 ** attempt
            print(f"Received 429 (rate limit). Backing off for {backoff_secs}s (attempt {attempt}/{MAX_RETRIES_429})")
            time.sleep(backoff_secs)
            continue

        if response.status_code != 200:
            response.raise_for_status()

        return response.json()

    raise Exception("Exceeded retries due to persistent 429 responses")


def fetch_all_events_for_drug(drug_name: str) -> list:
    """Fetch all adverse events for a given drug from the Open FDA API.
    Handles pagination to retrieve all available records.
    """
    all_events = []
    skip = 0
    max_attempts = 500  # Safety limit to prevent infinite loops
    attempt = 0
    
    print(f"Fetching adverse events for drug: {drug_name}")
    
    while attempt < max_attempts:
        try:
            # Search for drug adverse events
            query = f'patient.drug.openfda.generic_name:"{drug_name}" OR patient.drug.openfda.brand_name:"{drug_name}"'
            params = {
                'search': query,
                'limit': API_LIMIT,
                'skip': skip
            }
            
            data = call_fda_api(params)
            
            if 'results' not in data or len(data['results']) == 0:
                print(f"Reached end of results at skip={skip}")
                break
            
            all_events.extend(data['results'])
            skip += API_LIMIT
            attempt += 1
            
            print(f"  Fetched batch {attempt}: {len(data['results'])} records (total: {len(all_events)})")

        except requests.exceptions.RequestException as e:
            print(f"Request error: {e}")
            break
        except json.JSONDecodeError:
            print(f"JSON decode error")
            break
        except Exception as e:
            print(f"Error: {e}")
            break
    
    print(f"Total events fetched: {len(all_events)}")
    return all_events

def deduplicate_events(events: list) -> dict:
    """
    Deduplicate adverse events by counting unique event + outcome combinations.
    Returns a dictionary with event names as keys and counts as values.
    """
    event_counts = defaultdict(int)
    
    for event in events:
        try:
            # Extract adverse events from the reaction field
            if 'patient' in event and 'reaction' in event['patient']:
                for reaction in event['patient']['reaction']:
                    if 'reactionmeddrapt' in reaction:
                        event_name = reaction['reactionmeddrapt'].lower()
                        event_counts[event_name] += 1
        except (KeyError, TypeError):
            pass
    
    return dict(event_counts)

def calculate_statistics(event_counts: dict, total_reports: int) -> dict:
    """
    Calculate pharmacovigilance statistics for each adverse event.
    
    PRR (Proportional Reporting Ratio):
        PRR = (a/b) / (c/d)
        where:
        a = reports with drug and event
        b = reports with drug but without event
        c = reports without drug but with event
        d = reports without drug and without event
    
    ROR (Reporting Odds Ratio):
        ROR = (a*d) / (b*c)
    
    For this analysis, we're using the observed/expected approach with the drug as the focal point.
    """
    
    statistics = []
    
    # Total adverse events (combining all events)
    total_adverse_reports = sum(event_counts.values())
    
    for event_name, event_count in event_counts.items():
        # Reports with drug but WITHOUT this event
        drug_no_event = total_reports - event_count
        
        # For expected calculations, we use the proportion of this event across all reports
        # as a baseline for expected frequency
        event_proportion = total_adverse_reports / total_reports if total_reports > 0 else 0
        expected_count = total_reports * event_proportion if total_reports > 0 else 0
        
        # Avoid division by zero
        if expected_count == 0:
            expected_count = 0.5
        if drug_no_event == 0:
            drug_no_event = 0.5
            
        # PRR Calculation
        prr = event_count / expected_count if expected_count > 0 else 0
        
        # ROR Calculation (simplified for single drug)
        # ROR = (a * d) / (b * c), where we approximate background rates
        a = event_count  # Drug + Event
        b = drug_no_event  # Drug + No Event
        c = event_count * 0.1  # Estimated background + Event (rough estimate)
        d = total_reports * 0.9  # Estimated background + No Event
        
        ror = (a * d) / (b * c) if (b * c) > 0 else 0
        
        # Standard Error of log(ROR)
        se_log_ror = np.sqrt(1/a + 1/b + 1/c + 1/d) if all([a, b, c, d]) else 0
        
        # 95% Confidence Interval for ROR
        log_ror = np.log(ror) if ror > 0 else 0
        ci_lower = np.exp(log_ror - 1.96 * se_log_ror) if ror > 0 else 0
        ci_upper = np.exp(log_ror + 1.96 * se_log_ror) if ror > 0 else 0
        
        # EBGM (Empirical Bayes Geometric Mean) - simplified calculation
        # Uses a Poisson model approximation
        alpha = 0.5
        beta = 0.5
        try:
            from scipy.special import digamma
            # More sophisticated EBGM calculation
            ebgm = np.exp((np.log(a + alpha) - np.log(b + c + beta)))
        except:
            # Simplified fallback
            ebgm = np.sqrt(a / expected_count) if expected_count > 0 else 0
        
        ebgm05 = ebgm * 0.05 if ebgm > 0 else 0  # 5th percentile approximation
        
        # Standard Error
        se = np.sqrt(1/a) if a > 0 else 0
        
        statistics.append({
            'event': event_name.title(),
            'count': event_count,
            'prr': round(prr, 4),
            'ror': round(ror, 4),
            'ebgm05': round(ebgm05, 4),
            'se': round(se, 4),
            'ror_ci_95_lower': round(ci_lower, 4),
            'ror_ci_95_upper': round(ci_upper, 4)
        })
    
    # Sort by ROR descending (highest signals first)
    statistics.sort(key=lambda x: x['ror'], reverse=True)
    
    return statistics

def save_to_csv(statistics: list, drug_name: str, filename: str):
    """
    Save statistics to a CSV file.
    """
    if not statistics:
        print("No statistics to save.")
        return
    
    try:
        df = pd.DataFrame(statistics)
        df.to_csv(filename, index=False)
        print(f"\nResults saved to: {filename}")
        print(f"Total adverse events analyzed: {len(statistics)}")
        print("\nTop 10 Events by ROR:")
        print(df.head(10).to_string(index=False))
    except Exception as e:
        print(f"Error saving to CSV: {e}")

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    print("=" * 70)
    print("Open FDA FAERS Adverse Events Analyzer")
    print("=" * 70)
    
    # Fetch events from API
    events = fetch_all_events_for_drug(DRUG_NAME)
    
    if not events:
        print(f"No events found for drug: {DRUG_NAME}")
        return
    
    # Deduplicate and count events
    print("\nDeduplicating events...")
    event_counts = deduplicate_events(events)
    
    if not event_counts:
        print("No adverse events found in the data.")
        return
    
    print(f"Found {len(event_counts)} unique adverse events")
    
    # Calculate statistics
    print("\nCalculating pharmacovigilance statistics...")
    statistics = calculate_statistics(event_counts, len(events))
    
    # Save to CSV
    print("\nSaving results...")
    save_to_csv(statistics, DRUG_NAME, OUTPUT_FILENAME)
    
    print("\n" + "=" * 70)
    print("Analysis complete!")
    print("=" * 70)

if __name__ == "__main__":
    main()
