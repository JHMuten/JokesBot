import requests
import json
from datetime import datetime

def fetch_jokes(amount=10):
    """Fetch multiple jokes from JokeAPI."""
    url = f"https://v2.jokeapi.dev/joke/Any?blacklistFlags=nsfw,religious,political,racist,sexist,explicit&amount={amount}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        # API returns jokes in 'jokes' array when amount > 1
        if 'jokes' in data:
            return data['jokes']
        else:
            return [data]
    except requests.exceptions.RequestException as e:
        print(f"Error fetching jokes: {e}")
        return []

def is_duplicate(joke, existing_jokes):
    """Check if a joke already exists based on its ID."""
    joke_id = joke.get('id')
    return any(j.get('id') == joke_id for j in existing_jokes)

def save_jokes(jokes_data, filename="jokes.json"):
    """Save jokes to a local JSON file, avoiding duplicates."""
    if not jokes_data:
        return 0
    
    try:
        # Try to load existing jokes
        try:
            with open(filename, 'r') as f:
                existing_jokes = json.load(f)
        except FileNotFoundError:
            existing_jokes = []
        
        # Add new unique jokes
        new_count = 0
        for joke in jokes_data:
            if not is_duplicate(joke, existing_jokes):
                joke['fetched_at'] = datetime.now().isoformat()
                existing_jokes.append(joke)
                new_count += 1
        
        # Save back to file
        with open(filename, 'w') as f:
            json.dump(existing_jokes, f, indent=2)
        
        return new_count
        
    except Exception as e:
        print(f"Error saving jokes: {e}")
        return 0

if __name__ == "__main__":
    print("Fetching 100 unique jokes from JokeAPI...")
    print("="*50)
    
    target_jokes = 100
    total_fetched = 0
    batch_number = 0
    
    # Load existing jokes to check current count
    try:
        with open("jokes.json", 'r') as f:
            existing_jokes = json.load(f)
            current_count = len(existing_jokes)
    except FileNotFoundError:
        current_count = 0
    
    print(f"Starting with {current_count} existing jokes")
    
    # Keep fetching until we have at least 100 unique jokes
    while current_count < target_jokes:
        batch_number += 1
        print(f"\nFetching batch {batch_number}...")
        jokes = fetch_jokes(amount=10)
        
        if jokes:
            total_fetched += len(jokes)
            new_count = save_jokes(jokes)
            current_count += new_count
            print(f"  Fetched: {len(jokes)} jokes, New unique: {new_count}, Total unique: {current_count}/{target_jokes}")
        else:
            print("  Failed to fetch jokes, retrying...")
    
    # Trim to exactly 100 jokes if we have more
    if current_count > target_jokes:
        print(f"\nTrimming from {current_count} to exactly {target_jokes} jokes...")
        with open("jokes.json", 'r') as f:
            all_jokes = json.load(f)
        
        all_jokes = all_jokes[:target_jokes]
        
        with open("jokes.json", 'w') as f:
            json.dump(all_jokes, f, indent=2)
        
        current_count = target_jokes
    
    print("\n" + "="*50)
    print(f"Success! Saved exactly {current_count} unique jokes")
    print(f"Total API calls: {batch_number}")
    print(f"Total jokes fetched: {total_fetched}")
    print("="*50)
