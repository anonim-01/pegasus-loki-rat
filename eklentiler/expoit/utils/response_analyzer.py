import logging

def analyze_response(response, bts_id):
    if response is None:
        logging.error(f"No response for BTS ID {bts_id}")
        print(f"[ERROR] No response for BTS ID {bts_id}")
        return

    if response.status_code == 200:
        try:
            data = response.json()
            if "location" in data:
                logging.info(f"[SUCCESS] BTS ID {bts_id} returned location data: {data['location']}")
                print(f"[SUCCESS] BTS ID {bts_id} returned location data: {data['location']}")
            else:
                logging.warning(f"[WARN] BTS ID {bts_id} response missing location field")
                print(f"[WARN] BTS ID {bts_id} response missing location field")
        except ValueError:
            logging.error(f"[ERROR] BTS ID {bts_id} returned invalid JSON")
            print(f"[ERROR] BTS ID {bts_id} returned invalid JSON")
    else:
        logging.warning(f"[FAIL] BTS ID {bts_id} returned status {response.status_code}")
        print(f"[FAIL] BTS ID {bts_id} returned status {response.status_code}")
