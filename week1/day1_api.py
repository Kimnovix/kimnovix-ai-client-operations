import requests

# JSONPlaceholder provides stable, nested dummy data for testing
url = "https://jsonplaceholder.typicode.com/users/1"

try:
    response = requests.get(url, timeout=10)
    print("HTTP Status Code:", response.status_code)

    if response.status_code == 200:
        user_data = response.json()
        
        # Verify the expected structure exists before parsing
        if "name" in user_data and "address" in user_data:
            name = user_data["name"]
            
            # Extracting nested data (equivalent to reading folders within folders)
            city = user_data["address"]["city"]
            lat = user_data["address"]["geo"]["lat"]
            lng = user_data["address"]["geo"]["lng"]
            company_name = user_data["company"]["name"]

            print("\n--- USER SUMMARY ---")
            print(f"Name:        {name}")
            print(f"City:        {city}")
            print(f"Coordinates: {lat}, {lng}")
            print(f"Company:     {company_name}")
        else:
            print("\nUnexpected JSON structure received. Raw data payload:")
            print(user_data)
    else:
        print(f"Failed to fetch data. Server responded with: {response.status_code}")

except requests.exceptions.RequestException as e:
    print(f"Connection error: {e}")