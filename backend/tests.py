# Manual API test and Interactive Test
 
import requests
import os
import subprocess

BASE_URL = 'http://127.0.0.1:8000/api'
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))


def flush_database():
    print('DATABASE MANAGEMENT')    
    flush = input('\nFlush the database and start fresh? (y/n): ').strip().lower()
    if flush != 'y':
        print("Database unchanged.")
        return
    db_path = os.path.join(BACKEND_DIR, 'db.sqlite3')
    
    # Delete the database file
    if os.path.exists(db_path):
        os.remove(db_path)
        print("Deleted db.sqlite3")
    
    # Run migrations to recreate
    print("Running migrations...")
    result = subprocess.run(
        ['python', 'manage.py', 'migrate'],
        cwd=BACKEND_DIR,
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print("Database reset successfully!")
    else:
        print(f"Error: {result.stderr}")

def test_get_models():
    # Test GET models
    print('GET /api/models/')
    response = requests.get(f"{BASE_URL}/models/")
    print(f"Status: {response.status_code}")
    print('Response:')
    for model in response.json():
        print(f"  - {model['name']} ({model['id']})")

def test_get_sessions():
    # Test GET sessions
    print('GET /api/sessions/')
    response = requests.get(f"{BASE_URL}/sessions/")
    print(f"Status: {response.status_code}")
    print(f"Sessions: {response.json()}")

def test_get_responses():
    # Test GET responses
    print('GET /api/responses/')
    response = requests.get(f"{BASE_URL}/responses/")
    print(f"Status: {response.status_code}")
    print(f"Responses: {response.json()}")

def test_post_prompt():
    #Test POST prompt
    print('POST /api/prompt/')
    response = requests.post(
        f"{BASE_URL}/prompt/",
        json={
            'prompt': 'What is AI?',
            'model_ids': ['meta-llama/Llama-3.1-8B-Instruct']
            }
    )
    print(f"Status: {response.status_code}")
    data = response.json()
    if 'error' in data:
        print(f"  Error: {data['error']}")
    else:
        print(f"Session ID: {data.get('session_id')}")
        print(f"Prompt: {data.get('prompt')}")
        for r in data.get('responses', []):
            print(f"Model: {r.get('model_name')}")
            print(f"Response: {r.get('response', '')[:100]}")

# Interactive test for any prompt on a specific model
def interactive_test():
    print('INTERACTIVE BACKEND TEST')
    
    # Get available models
    response = requests.get(f"{BASE_URL}/models/")
    models = response.json()
    
    # Display models
    if not models:
        print("No models available.")
        return
    print('\nAvailable models:')
    for i, model in enumerate(models, 1):
        print(f"  {i}. {model['name']}")
    
    # Get user selection
    while True:
        try:
            choice = input(f"\nSelect a model (1-{len(models)}): ").strip()
            choice_num = int(choice)
            if 1 <= choice_num <= len(models):
                selected_model = models[choice_num - 1]
                break
            else:
                print(f"Please enter a number between 1 and {len(models)}")
        except ValueError:
            print('Please enter a valid number')
    print(f"\nSelected: {selected_model['name']}")
    
    # Get user prompt
    prompt = input('\nEnter your prompt: ').strip()
    if not prompt:
        print('No prompt entered. Exiting.')
        return
    
    # Send request to API
    print(f"\nSending prompt through BACKEND to {selected_model['name']}")    
    response = requests.post(
        f"{BASE_URL}/prompt/",
        json={
            'prompt': prompt,
            'model_ids': [selected_model['id']]
        }
    )
    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        print(response.json())
        return
    data = response.json()
    
    # Display response
    print(f"Model: {selected_model['name']}")
    print(f"\nPrompt: {data.get('prompt')}\n")
    
    for r in data.get('responses', []):
        if r.get('success'):
            print(f"Response: {r.get('response')}")
        else:
            print(f"Error: {r.get('error')}")

def main():
    print('Backend Interactive Tests')
    flush_database()
    test_get_models()
    test_get_sessions()
    test_get_responses()
    test_post_prompt()
    run_interactive = input('\nRun interactive model test? (y/n): ').strip().lower()
    if run_interactive == 'y':
        interactive_test()

if __name__ == '__main__':
    main()

