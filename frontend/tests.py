# Manual API test and Interactive Test

import requests

# Frontend URL (talks to frontend, which proxies to backend)
FRONTEND_URL = 'http://127.0.0.1:3000'
# Backend URL (for comparison/verification)
BACKEND_URL = 'http://127.0.0.1:8000/api'

# HTTP Status Check
def test_frontend_index():
    print(f"GET {FRONTEND_URL}")
    try:
        response = requests.get(f"{FRONTEND_URL}/", timeout=10)
        print(f"Status: {response.status_code}")
    except requests.RequestException as e:
        print(f"Exception: {e}")

# Automated test of prompt and response 
def test_frontend_chat_endpoint():
    print('POST /chat/')
    
    # Use first model available from backend
    try:
        models_response = requests.get(f"{BACKEND_URL}/models/", timeout=5)
        models = models_response.json()
        if not models:
            print("No models available from backend")
            return
        test_model_id = models[0]['id']
        test_model_name = models[0]['name']
        print(f"Using model: {test_model_name}")
        
    except requests.RequestException as e:
        print(f"Exception:{e}")
        return
    
    # Send hardcoded prompt, print response
    try:
        response = requests.post(f"{FRONTEND_URL}/chat/",
                                    json={'prompt': 'What is AI?',
                                          'model_ids': [test_model_id]
                                          },
                                    timeout=60
                                )
        print(f"Send Prompt Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Prompt: {data['prompt']}")
            print(f"50 Char Response: {data['responses'][0]['response'][:50]}")
            
    except requests.RequestException as e:
        print(f"Exception: {e}")

# Interactive test
def interactive_test():
    print('INTERACTIVE FRONTEND TEST')
    
    # Get models from backend
    response = requests.get(f"{BACKEND_URL}/models/")
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
    
    # Send through frontend
    print(f"\nSending prompt through FRONTEND to {selected_model['name']}")
    response = requests.post(
        f"{FRONTEND_URL}/chat/",
        json={
            'prompt': prompt,
            'model_ids': [selected_model['id']]
        },
        timeout=60
    )
    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        print(response.json())
        return
        
    data = response.json()    
    # Display response
    print(f"Model: {selected_model['name']}")
    print(f"\nPrompt: {prompt}\n")
        
    for r in data.get('responses', []):
        if r.get('success'):
            print(f"Response: {r.get('response')}")
        else:
            print(f"Error: {r.get('error')}")

# Check if both servers are running
def check_servers():
    print('CHECKING SERVERS')
    # Check backend
    try:
        response = requests.get(f"{BACKEND_URL}/models/")
        print(f"Backend running at {BACKEND_URL}")
    except requests.RequestException:
        print(f"Backend NOT running at {BACKEND_URL}")
        print("Start with: cd backend && python manage.py runserver")
        return False
    # Check frontend
    try:
        response = requests.get(f"{FRONTEND_URL}/", timeout=2)
        print(f"Frontend running at {FRONTEND_URL}")
    except requests.RequestException:
        print(f"Frontend NOT running at {FRONTEND_URL}")
        print("Start with: cd frontend && python manage.py runserver 3000")
        return False
    return True


def main():
    print("Frontend Interactive Tests")
    if not check_servers():
        print("\nPlease start both servers and try again.")
        return
    test_frontend_index()    

    run_chat = input('Run Automated Chat Test? (y/n): ').strip().lower()
    if run_chat == 'y':
        print()
        test_frontend_chat_endpoint()
    
    run_interactive = input('Run Interactive Chat Test? (y/n): ').strip().lower()
    if run_interactive == 'y':
        print()
        interactive_test()

if __name__ == '__main__':
    main()
